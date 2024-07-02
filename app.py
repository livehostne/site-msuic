from flask import Flask, render_template, request, Response
from pytube import YouTube, Search
from pymongo import MongoClient
from gridfs import GridFS
import threading
import time
import os

app = Flask(__name__)

# Configuração do MongoDB
client = MongoClient('mongodb+srv://joaoz:9agos2010@musicas.uapztfb.mongodb.net/?retryWrites=true&w=majority')
db = client['musicas_db']
fs = GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    search = Search(query)
    results = search.results[:5]  # Limita para os primeiros 5 resultados
    video_info = []

    for video in results:
        yt = YouTube(video.watch_url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        video_info.append({
            'title': video.title,
            'thumbnail_url': video.thumbnail_url,
            'video_id': video.video_id,
            'audio_url': audio_stream.url
        })

    return render_template('results.html', results=video_info)


@app.route('/download/<video_id>')
def download(video_id):
    yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
    stream = yt.streams.filter(only_audio=True).first()
    audio_data = stream.download()

    with open(audio_data, 'rb') as f:
        audio_binary = f.read()

    os.remove(audio_data)
    
    # Armazenar no MongoDB usando GridFS
    musica_id = fs.put(audio_binary, filename=f"{yt.title}.mp3")

    # Configurar remoção após 5 segundos
    def delete_file(musica_id):
        time.sleep(5)
        fs.delete(musica_id)

    threading.Thread(target=delete_file, args=(musica_id,)).start()

    # Preparar o nome do arquivo para o cabeçalho de resposta
    filename = f"{yt.title}.mp3"
    encoded_filename = filename.encode('utf-8')

    return Response(
        audio_binary,
        mimetype="audio/mp3",
        headers={"Content-Disposition": f"attachment;filename={encoded_filename.decode('latin-1')}"}
    )

if __name__ == '__main__':
    app.run(debug=True)