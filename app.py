from flask import Flask, render_template, request, redirect
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId


load_dotenv()

print(os.getenv("MONGO_URI"))

app = Flask(__name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client.menuDB

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
)

@app.route('/')
def index():
    items = list(db.items.find())
    return render_template('index.html', items=items)

@app.route('/add', methods=['POST'])
def add_item():
    name = request.form['name']
    description = request.form['description']
    image = request.files['image']

    image_url = ''
    if image:
        upload_result = cloudinary.uploader.upload(image)
        image_url = upload_result['secure_url']

    db.items.insert_one({
        'name': name,
        'description': description,
        'imageUrl': image_url
    })

    return redirect('/')

@app.route('/delete/<item_id>', methods=['POST'])
def delete_item(item_id):
    db.items.delete_one({'_id': ObjectId(item_id)})
    return redirect('/')

@app.route('/edit/<item_id>', methods=['GET'])
def edit_item(item_id):
    item = db.items.find_one({'_id': ObjectId(item_id)})
    return render_template('edit.html', item=item)

@app.route('/update/<item_id>', methods=['POST'])
def update_item(item_id):
    name = request.form['name']
    description = request.form['description']
    image = request.files.get('image')

    update_data = {
        'name': name,
        'description': description,
    }

    if image:
        upload_result = cloudinary.uploader.upload(image)
        update_data['imageURL'] = upload_result['secure_url']

    db.items.update_one({'_id': ObjectId(item_id)}, {'$set': update_data}) 

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

