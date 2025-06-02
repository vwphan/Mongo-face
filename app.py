import os
from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv # Import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24) # Add a secret key for flash messages

# Configure MongoDB from environment variables
mongo_uri = os.getenv("MONGO_URI")
collection_name = os.getenv("MONGO_COLLECTION_NAME")

if not mongo_uri or not collection_name:
    raise ValueError("MONGO_URI and MONGO_COLLECTION_NAME must be set in the .env file or environment variables.")

mongo = MongoClient(mongo_uri)
db = mongo.get_database()
my_collection = db[collection_name]

@app.route('/')
def index():
    # Fetch all documents from the collection
    items = my_collection.find()
    return render_template('index.html', items=items, collection_name=collection_name) # Pass collection_name to template

@app.route('/add', methods=['POST'])
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        if name:
            new_item = {"name": name}
            if description:
                new_item["description"] = description
            
            my_collection.insert_one(new_item)
            flash('Item added successfully!', 'success')
        else:
            flash('Name is required to add an item.', 'error')
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_item():
    if request.method == 'POST':
        item_id = request.form.get('delete_id')
        
        if item_id:
            try:
                # MongoDB's _id is an ObjectId, so we need to convert the string to ObjectId
                result = my_collection.delete_one({"_id": ObjectId(item_id)})
                if result.deleted_count > 0:
                    flash('Item deleted successfully!', 'success')
                else:
                    flash('No item found with that ID.', 'warning')
            except Exception as e:
                flash(f'Error deleting item: {e}', 'error')
        else:
            flash('Item ID is required for deletion.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

