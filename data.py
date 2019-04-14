import os
import sys
import argparse
import json
import urllib.request as req
import urllib.error as urlerr
import time

import spotipy
import spotipy.oauth2 as auth
import spotipy.client as spcl

import util


class SpotifyRefresher:
    def __init__(self, refresh_interval=5*60):
        self._interval = refresh_interval
        self._sp = None
        self._init_time = None
        self.refresh()

    def refresh(self):
        self._sp = SpotifyRefresher._spotipy_factory()
        self._init_time = time.time()

    @property
    def client(self):
        if self._refresh_required:
            self.refresh()
        
        return self._sp

    @property
    def _refresh_required(self):
        return (time.time() - self._init_time) > self._interval

    @staticmethod
    def _spotipy_factory():
        # authorize
        credentials = auth.SpotifyClientCredentials()
        token_info = credentials.get_access_token()

        # create our client
        return spotipy.Spotify(token_info)
    
    def iterate(self, response):
        for item in response['items']:
            yield item
        
        while response['next']:
            response = self.client.next(response)

            for item in response['items']:
                yield item


def parse_args(argv):
    parser = argparse.ArgumentParser(description='A utility for scraping the Spotify API for album artwork!')

    parser.add_argument('--album-file', default='./out/albums.json', 
        help='The path to the image list file. If this file exists and the overwrite flag '
             'is not specified, then the cached listing will be used. Otherwise, a new file '
             'is created and saved to')
    parser.add_argument('--output-dir', default='./out/data',
        help='The directory to output the downloaded images to')
    parser.add_argument('--overwrite', action='store_true',
        help='Flag that causes image files to be redownloaded, and the image list file to be '
             'regenerated if it already exists')
    parser.add_argument('--username', default='spotify',
        help='The username of the user we want to pull playlists from')
    parser.add_argument('--artist-file', default='./out/artists.json')

    return parser.parse_args(argv)

def scrape_discog(sp, artist_id, album_dict):
    albums = sp.client.artist_albums(artist_id)

    for album in sp.iterate(albums):
        album_id = album['id']
        album_name = album['name']

        # don't add if we already have this album
        if album_id in album_dict:
            continue
        
        # skip if there are no available images
        if not album['images']:
            continue
        
        # skip if this is a compilation album
        if album['album_type'] == 'compilation':
            continue
            
        for artist in album['artists']:
            if artist['name'].lower() == 'various artists':
                # don't include compilations
                continue
        
        album_dict[album_id] = {
            'name': album_name,
            'url': album['images'][0]['url'],
        }

def scrape_playlist(sp, artist_dict, playlist_id, username):
    playlist = sp.client.user_playlist(username, playlist_id=playlist_id)
    
    for track in sp.iterate(playlist['tracks']):
        # handle weird edge case where track is empty
        if not track['track']:
            continue

        for artist in track['track']['artists']:
            artist_id = artist['id']
            if artist_id in artist_dict:
                continue
            
            artist_dict[artist_id] = {
                'name': artist['name']
            }


def get_artist_data(sp, username, output_file, overwrite=False):
    if os.path.isfile(output_file) and not overwrite:
        print('Pulling cached artist data... ', end='')
        artist_dict = read_json(output_file)
        print('Done')
        return artist_dict

    print('Scraping artist data... ')
    user_playlists = sp.client.user_playlists(username)
    artist_dict = {}
    playlist_count = user_playlists['total']
    for i, playlist in enumerate(sp.iterate(user_playlists)):
        sys.stdout.write("\033[K")
        print('[%i/%i] Playlist name: %s\r'%(i + 1, playlist_count, playlist['name']), end='')

        scrape_playlist(sp, artist_dict, playlist['id'], username)
    
    print()
    print('Scrape complete\n')

    print('Writing to file... ', end='')
    export_to_json(artist_dict, output_file)
    print('Done')
    
    return artist_dict

def export_to_json(data_dict, output_file):
    dir_path = os.path.dirname(output_file)
    util.makedirs(dir_path)

    with open(output_file, 'w') as fp:
        json.dump(data_dict, fp)

def read_json(input_file):
    with open(input_file, 'r') as fp:
        return json.load(fp)

def download_image(out_dir, album_id, album_image):
    filename = '%s.jpeg'%album_id
    filepath = os.path.join(out_dir, '%s'%filename)

    if os.path.exists(filepath):
        return

    req.urlretrieve(album_image, filepath)

def download_images(album_dict, output_directory):
    util.makedirs(output_directory)
    retrieved_count = 0
    album_count = len(album_dict)
    for album_id, album_data in album_dict.items():
        sys.stdout.write("\033[K")
        print('[%i/%i] Album name: %s\r'%(retrieved_count, album_count, album_data['name']), end='')

        try:
            download_image(output_directory, album_id, album_data['url'])
        except (urlerr.HTTPError, urlerr.ContentTooShortError):
            print('Could not retrieve %s'%album['name'])
        
        retrieved_count += 1

def get_album_data(sp, artist_data, album_output_file, overwrite=False):
    if os.path.isfile(album_output_file) and not overwrite:
        print('Pulling cached album data... ', end='')
        album_dict = read_json(album_output_file)
        print('Done')
        return album_dict

    album_dict = {}
    artist_count = len(artist_data)
    for i, (artist_id, artist_data) in enumerate(artist_data.items()):
        sys.stdout.write("\033[K")
        print('[%i/%i] Artist: %s\r'%(i + 1, artist_count, artist_data['name']), end='')
        scrape_discog(sp, artist_id, album_dict)

    print()
    print('Writing to file... ', end='')
    export_to_json(album_dict, album_output_file)

    return album_dict


def download_image_data(username, data_directory, artist_output_file, album_output_file, overwrite):
    # create our client
    sp = SpotifyRefresher()

    artist_dict = get_artist_data(sp, username, artist_output_file, overwrite=overwrite)

    print()

    album_dict = get_album_data(sp, artist_dict, album_output_file, overwrite=overwrite)

    print()

    # download all of the images in our image list
    print('Beginning image download...')
    download_images(album_dict, data_directory)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    download_image_data(args.username, args.output_dir, args.artist_file, args.album_file, overwrite=args.overwrite)