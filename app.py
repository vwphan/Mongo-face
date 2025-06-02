import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# A secret key is required for Flask sessions to work.
# In a production environment, use a strong, randomly generated key stored securely.
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24)) 

# Configure MongoDB from environment variables
mongo_uri = os.getenv("MONGO_URI")

if not mongo_uri:
    raise ValueError("MONGO_URI must be set in the .env file or environment variables.")

mongo = MongoClient(mongo_uri)
db = mongo.get_database() # This will get the database specified in the MONGO_URI

# --- Helper function to get the current collection ---
def get_current_collection():
    if 'current_collection_name' not in session:
        # If no collection is selected yet, try to get the first one or default
        collection_names = db.list_collection_names()
        if collection_names:
            session['current_collection_name'] = collection_names[0]
        else:
            # Handle case where database is empty, perhaps create a default one
            # For now, let's assume there's at least one collection or the user will create one
            return None # Or raise an error, or redirect to a creation page
    
    return db[session['current_collection_name']]

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get all collection names from the connected database
    all_collection_names = db.list_collection_names()

    # Handle collection switching via POST request
    if request.method == 'POST':
        selected_collection = request.form.get('selected_collection')
        if selected_collection and selected_collection in all_collection_names:
            session['current_collection_name'] = selected_collection
            flash(f"Switched to collection '{selected_collection}'.", 'info')
        else:
            flash("Invalid collection selected.", 'error')
        return redirect(url_for('index')) # Redirect to GET to avoid form resubmission

    # Set initial collection if not already set in session
    if 'current_collection_name' not in session and all_collection_names:
        session['current_collection_name'] = all_collection_names[0]
    elif not all_collection_names:
        session['current_collection_name'] = None # No collections exist yet

    current_collection_name = session.get('current_collection_name')
    items = []
    if current_collection_name:
        current_collection = db[current_collection_name]
        items = current_collection.find()

    return render_template('index.html', 
                           items=items, 
                           all_collection_names=all_collection_names,
                           current_collection_name=current_collection_name)

@app.route('/add', methods=['POST'])
def add_item():
    current_collection = get_current_collection()
    if not current_collection:
        flash("No collection selected or available to add items.", 'error')
        return redirect(url_for('index'))

    name = request.form.get('name')
    description = request.form.get('description')

    if name:
        new_item = {"name": name}
        if description:
            new_item["description"] = description
        
        current_collection.insert_one(new_item)
        flash(f'Item added to "{session["current_collection_name"]}" successfully!', 'success')
    else:
        flash('Name is required to add an item.', 'error')
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_item():
    current_collection = get_current_collection()
    if not current_collection:
        flash("No collection selected or available to delete items.", 'error')
        return redirect(url_for('index'))

    item_id = request.form.get('delete_id')
    
    if item_id:
        try:
            # MongoDB's _id is an ObjectId, so we need to convert the string to ObjectId
            result = current_collection.delete_one({"_id": ObjectId(item_id)})
            if result.deleted_count > 0:
                flash(f'Item deleted from "{session["current_collection_name"]}" successfully!', 'success')
            else:
                flash('No item found with that ID in the current collection.', 'warning')
        except Exception as e:
            flash(f'Error deleting item: {e}', 'error')
    else:
        flash('Item ID is required for deletion.', 'error')
    return redirect(url_for('index'))

@app.route('/create_collection', methods=['POST'])
def create_collection():
    new_collection_name = request.form.get('new_collection_name')
    if new_collection_name:
        # MongoDB creates a collection implicitly when you insert the first document.
        # However, to explicitly create it and make it appear in list_collection_names immediately,
        # you can insert a dummy document and then delete it, or use create_collection.
        if new_collection_name not in db.list_collection_names():
            # Explicitly create the collection
            db.create_collection(new_collection_name)
            flash(f"Collection '{new_collection_name}' created successfully!", 'success')
            session['current_collection_name'] = new_collection_name # Switch to new collection
        else:
            flash(f"Collection '{new_collection_name}' already exists.", 'warning')
    else:
        flash("Collection name cannot be empty.", 'error')
    return redirect(url_for('index'))

@app.route('/delete_collection', methods=['POST'])
def delete_collection():
    collection_to_delete = request.form.get('collection_to_delete')
    if collection_to_delete and collection_to_delete in db.list_collection_names():
        if collection_to_delete == session.get('current_collection_name'):
            session.pop('current_collection_name', None) # Clear current selection if deleting it

        db.drop_collection(collection_to_delete)
        flash(f"Collection '{collection_to_delete}' deleted successfully!", 'success')
    else:
        flash("Invalid collection selected for deletion.", 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
