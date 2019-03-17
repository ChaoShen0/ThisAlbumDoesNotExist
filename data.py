import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


def scrape_album_art():

    auth = SpotifyClientCredentials()


    token_info = auth.get_access_token()

    sp = spotipy.Spotify(token_info)

    results = sp.user_playlists('spotify')


    items = results['items']
    while results['next']:
        results = sp.next(results)
        items.extend(results['items'])
    
    print([t['name'] for t in items])


if __name__ == '__main__':
    scrape_album_art()