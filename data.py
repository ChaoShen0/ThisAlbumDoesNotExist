import os
import sys
import argparse
import json
import urllib.request as req
import urllib.error as urlerr

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import util

def parse_args(argv):
    parser = argparse.ArgumentParser(description='A utility for scraping the Spotify API for album artwork!')

    parser.add_argument('--list-file', default='./out/data/images.lst', 
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

    return parser.parse_args(argv)


def spotipy_iter(sp, response):
    for item in response['items']:
        yield item
    
    while response['next']:
        response = sp.next(response)
        for item in response['items']:
            yield item

def scrape_discog(sp, artist_id):
    albums = sp.artist_albums(artist_id)

    scraped_albums = []
    for album in spotipy_iter(sp, albums):
        album_id = album['id']

        # skip the album if we already have it or it doesn't have images
        if album_id in scraped_albums or not album['images']:
            continue

        scraped_albums.append({
            'name': album['name'],
            'url': album['images'][0]['url'],\
            'id': album_id
        })

    return scraped_albums

def scrape_playlist(sp, album_dict, playlist_id, username):
    playlist = sp.user_playlist(username, playlist_id=playlist_id)
    
    track_count = playlist['tracks']['total']
    for i, track in enumerate(spotipy_iter(sp, playlist['tracks'])):
        for artist in track['track']['artists']:
            artist_name = artist['name']
            artist_id = artist['id']

            sys.stdout.write("\033[K")
            print('\t[%i/%i] Artist name: %s\r'%(i+1, track_count, artist_name), end='')
            
            if artist_id in album_dict:
                continue

            album_dict[artist_id] = {
                'name': artist_name,
                'albums': scrape_discog(sp, artist['id']),
            }

    print()
    return album_dict

def scrape_album_artwork(sp, username):
    user_playlists = sp.user_playlists(username)
    album_dict = {}
    playlist_count = user_playlists['total']
    for i, playlist in enumerate(spotipy_iter(sp, user_playlists)):
        print('[%i/%i] Playlist name: %s'%(i + 1, playlist_count, playlist['name']))
        album_dict.update(scrape_playlist(sp, album_dict, playlist['id'], username))
    
    print()
    return album_dict

def write_to_file(album_dict, output_file):
    dir_path = os.path.dirname(output_file)
    util.makedirs(dir_path)

    with open(output_file, 'w') as fp:
        json.dump(album_dict, fp)

def download_image(out_dir, album_id, album_image, overwrite=False):
    filename = '%s.jpeg'%album_id
    filepath = os.path.join(out_dir, '%s'%filename)

    if not overwrite and os.path.exists(filepath):
        return

    req.urlretrieve(album_image, filepath)

def download_images(artist_dict, output_directory, overwrite=False):
    util.makedirs(output_directory)
    total_album_count = sum(len(a['albums']) for a in artist_dict.values())
    retrieved_count = 0
    for artist_info in artist_dict.values():
        for album in artist_info['albums']:
            sys.stdout.write("\033[K")
            print('\t[%i/%i] Album name: %s\r'%(retrieved_count, total_album_count, album['name']), end='')

            try:
                download_image(output_directory, album['id'], album['url'], overwrite=overwrite)
            except (urlerr.HTTPError, urlerr.ContentTooShortError):
                print('Could not retrieve %s by %s'%(album['name'], artist_info['name']))
            
            retrieved_count += 1
            

def download_image_data(username, data_directory, list_file, overwrite=False):
    # authorize
    auth = SpotifyClientCredentials()
    token_info = auth.get_access_token()

    # create our client
    sp = spotipy.Spotify(token_info)
    
    if os.path.exists(list_file) and not overwrite:
        print('Pulling cached list file from %s'%list_file)
        with open(list_file, 'r') as fp:
            album_dict = json.load(fp)
    else:
        print('Scraping data from Spotify')
        print('Grab yourself a beer, this is going to take a while\n')

        album_dict = scrape_album_artwork(sp, username)

        # write our image url list to a file
        write_to_file(album_dict, list_file)

    # download all of the images in our image list
    print('Beginning image download...')
    download_images(album_dict, data_directory, overwrite=overwrite)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    download_image_data(args.username, args.output_dir, args.list_file, overwrite=args.overwrite)