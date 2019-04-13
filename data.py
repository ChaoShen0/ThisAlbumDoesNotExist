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

    discog_dict = {}
    for album in spotipy_iter(sp, albums):
        album_id = album['id']

        # skip the album if we already have it or it doesn't have images
        if album_id in discog_dict or not album['images']:
            continue

        # it could be this is just a feature, assuming main artist is listed first
        artist_name = album['artists'][0]['name'] if album['artists'] else 'NA'

        discog_dict[album_id] = {
            'name': album['name'],
            'url': album['images'][0]['url'],
            'artist': artist_name
        }

    return discog_dict

def scrape_playlist(sp, playlist_id, username):
    playlist = sp.user_playlist(username, playlist_id=playlist_id)
    
    playlist_dict = {}
    for track in spotipy_iter(sp, playlist['tracks']):
        for artist in track['track']['artists']:
            playlist_dict.update(scrape_discog(sp, artist['id']))
    
    return playlist_dict

def scrape_album_artwork(sp, username):
    user_playlists = sp.user_playlists(username)
    album_dict = {}

    for playlist in spotipy_iter(sp, user_playlists):
        album_dict.update(scrape_playlist(sp, playlist['id'], username))
    
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

def download_images(album_dict, output_directory, overwrite=False):
    util.makedirs(output_directory)
    for album_id, album_info in album_dict.items():
        try:
            download_image(output_directory, album_id, album_info['url'], overwrite=overwrite)
        except (urlerr.HTTPError, urlerr.ContentTooShortError):
            print('Could not retrieve %s by %s'%(album_info['name'], album_info['artist']))

def download_image_data(username, data_directory, list_file, overwrite=False):
    # authorize
    auth = SpotifyClientCredentials()
    token_info = auth.get_access_token()

    # create our client
    sp = spotipy.Spotify(token_info)
    
    if os.path.exists(list_file):
        album_dict = json.load(list_file)
    else:
        album_dict = scrape_album_artwork(sp, username)

        # write our image url list to a file
        write_to_file(album_dict, list_file)

    # download all of the images in our image list
    download_images(album_dict, data_directory, overwrite=overwrite)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    download_image_data(args.username, args.output_dir, args.list_file, overwrite=args.overwrite)