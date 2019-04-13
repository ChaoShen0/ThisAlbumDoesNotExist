import os
import json
import urllib.request as req
import urllib.error as urlerr

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import util

# SPOTIFY_USERNAME = 'spotify'
SPOTIFY_USERNAME = 'lyoaqbt6veuxjxk5jwappooa3'
OUT_DIR = './out/data/'
IMAGE_LIST_FILENAME = './out/data/images.lst'
DOWNLOAD_IMAGES = True


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

def scrape_playlist(sp, playlist_id):
    playlist = sp.user_playlist(SPOTIFY_USERNAME, playlist_id=playlist_id)
    
    playlist_dict = {}
    for track in spotipy_iter(sp, playlist['tracks']):
        for artist in track['track']['artists']:
            playlist_dict.update(scrape_discog(sp, artist['id']))
    
    return playlist_dict

def scrape_album_artwork(sp, username):
    user_playlists = sp.user_playlists(SPOTIFY_USERNAME)
    album_dict = {}

    for playlist in spotipy_iter(sp, user_playlists):
        album_dict.update(scrape_playlist(sp, playlist['id']))
    
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
    util.makedirs(OUT_DIR)
    for album_id, album_info in album_dict.items():
        try:
            download_image(OUT_DIR, album_id, album_info['url'], overwrite=overwrite)
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
    download_image_data(SPOTIFY_USERNAME, OUT_DIR, IMAGE_LIST_FILENAME)