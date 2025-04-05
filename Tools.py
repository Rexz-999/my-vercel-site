import os
import yt_dlp
import requests
from pytube import YouTube

def download_youtube_content():
    # Get the YouTube video URL from the user

    url = input("Enter the YouTube video link: ")
    try:
        yt = YouTube(url)
    except Exception as e:
        print(f"Error: {e}")
        return

    print("\nChoose an option:")
    print("1 - Download video in MP4 format")
    print("2 - Download audio in MP3 format")
    print("3 - Download video thumbnail")

    choice = input("\nEnter your choice (1/2/3): ")

    try:
        if choice == '1':
            print("Downloading video in MP4 format...")
            ydl_opts = {
                'format': 'best',
                'outtmpl': '%(title)s.%(ext)s',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print("Video downloaded successfully!")

        elif choice == '2':
            print("Downloading audio in MP3 format...")
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Prefer M4A
                'extractaudio': True,
                'audioformat': 'mp3',
                'outtmpl': '%(title)s.mp3',  # Enforce .mp3 extension
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print("Audio downloaded and converted to MP3 successfully!")


        elif choice == '3':
            print("Downloading thumbnail...")
            thumbnail_url = yt.thumbnail_url
            thumbnail_file = "thumbnail.jpg"  # Generic name to avoid dependency on title
            response = requests.get(thumbnail_url)
            with open(thumbnail_file, 'wb') as file:
                file.write(response.content)
            print(f"Thumbnail downloaded successfully as {thumbnail_file}!")

        else:
            print("Invalid choice. Please try again.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_youtube_content()
