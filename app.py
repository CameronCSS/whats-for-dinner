from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
import json
import random
from flask_cors import CORS


from datetime import datetime, timedelta

from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from datetime import date

from helpers import login_required


# Configure application
app = Flask(__name__, static_url_path='/static')


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_DURATION"] = timedelta(days=30)


Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    user_info = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = user_info[0]['username'] if user_info else ''
    user_id = session["user_id"]
    all_ingredients = db.execute("SELECT * FROM ingredients ORDER BY name")
    ingredients_on_hand = db.execute("SELECT * FROM on_hand WHERE user_id = ?", session["user_id"])

    # Fetch all recipes (or apply any filters if needed)
    recipes = db.execute("SELECT * FROM recipes ORDER BY name")

    total_count = db.execute("SELECT recipe_id, COUNT(ingredient_id) AS ingredient_count FROM relate GROUP BY recipe_id")
    # Fetch last shopped dates for each recipe
    last_shopped_dates = db.execute("SELECT recipes.recipe_id, MAX(last_shopped.date_shopped) as last_shopped_date FROM recipes LEFT JOIN last_shopped ON recipes.recipe_id = last_shopped.recipe_id WHERE user_id = ? GROUP BY recipes.recipe_id", user_id)
    # Convert the results into a dictionary
    last_shopped_dict = {item['recipe_id']: item['last_shopped_date'] for item in last_shopped_dates}
    today = date.today().strftime('%m-%d-%Y')

    fav_store = db.execute("SELECT store FROM fav_store WHERE user_id = ?", user_id)
    if fav_store:
        session['selected_store'] = fav_store[0]['store']
    else:
        session['selected_store'] = 'walmart'

    if request.method == "POST":

        # Handling AJAX request to add a recipe to the selected list
        recipe_id = request.form.get('recipe_id')
        recipe_name = request.form.get('recipe_name')

        if recipe_id:
            if 'selected_recipes' not in session:
                session['selected_recipes'] = []
            if not any(r['id'] == recipe_id for r in session['selected_recipes']):
                session['selected_recipes'].append({'id': recipe_id, 'name': recipe_name})
            return jsonify(success=True)

        selected_recipes = session.get('selected_recipes', [])

        # Check if no recipes are selected when trying to generate a shopping list
        if 'selected_recipes' in request.form and not selected_recipes:
            flash("Please select recipes to generate a shopping list.", "error")
            return redirect("/")

        selected_recipe_ids = [recipe['id'] for recipe in selected_recipes if isinstance(recipe, dict) and 'id' in recipe]

        if selected_recipe_ids:
            placeholders = ', '.join(['?'] * len(selected_recipe_ids))
            ingredients = db.execute("SELECT * FROM ingredients i JOIN relate r ON i.ingredient_id = r.ingredient_id WHERE r.recipe_id IN ({})".format(placeholders), *selected_recipe_ids)
            session['selected_ingredients'] = [dict(ingredient) for ingredient in ingredients]
            return redirect('shopping_list')

        # Calculate the date 7 days ago in the appropriate format
        seven_days_ago = datetime.now() - timedelta(days=7)
        formatted_date = seven_days_ago.strftime('%m-%d-%Y')

        # Execute the SQL statement to delete older ingredients
        db.execute("DELETE FROM on_hand WHERE user_id = ? AND date_updated < ?", session["user_id"], formatted_date)

        if 'ingredient_name' in request.form:
            ingredient_name = request.form.get("ingredient_name").title()

            # Check if ingredient already on hand
            existing = db.execute("SELECT * FROM on_hand WHERE ingredient_name = ?", ingredient_name)
            if existing:
                flash("Ingredient already on hand", "error")
                return redirect("/")

            check_ingredient = db.execute("SELECT * FROM Ingredients WHERE name = ?", ingredient_name)
            if not check_ingredient:
                flash("Ingredient name must be in ingredient list", "error")
                return redirect("/")

            # Insert new ingredient into the database
            db.execute("INSERT OR REPLACE INTO on_hand (user_id, ingredient_name, date_updated) VALUES (?, ?, ?)", user_id, ingredient_name, today)
            flash("On hand Ingredient Added", "success")
            return redirect("/")

    else:
        selected_recipes = session.get('selected_recipes', [])

        filter_type = request.args.get('filter', 'no_filter')  # Default to 'no_filter'
        # Map filter to title
        filter_titles = {
        'no_filter': 'All Recipes',
        'on_hand': 'Recipes with Some Ingredients On Hand',
        'all_on_hand': 'Recipes with All Ingredients On Hand',
        'last_week': 'Recipes Shopped in the last 7 days',
        'last_month': 'Recipes sopped in the Last 30 Days',
        'only_faves': 'My Favorite Recipes'
        }

        # Set the title based on the current filter
        title = filter_titles.get(filter_type, 'All Recipes')

        no_filter = filter_type == 'no_filter'
        some_on_hand = filter_type == 'on_hand'
        all_on_hand = filter_type == 'all_on_hand'
        last_week = filter_type == 'last_week'
        last_month = filter_type == 'last_month'
        only_faves = filter_type == 'only_faves'

        # Get the total ingredient count for each recipe
        total_count = db.execute("SELECT recipe_id, COUNT(ingredient_id) AS ingredient_count FROM relate GROUP BY recipe_id")
        total_count_dict = {item['recipe_id']: item['ingredient_count'] for item in total_count}

        # Get the count of on-hand ingredients for each recipe
        on_hand_count = db.execute("SELECT recipe_id , COUNT(ingredient_id) AS on_hand_count FROM relate WHERE ingredient_id IN(SELECT ingredient_id FROM ingredients WHERE name IN (SELECT ingredient_name FROM on_hand WHERE user_id = ?)) GROUP BY recipe_id", user_id)
        on_hand_count_dict = {item['recipe_id']: item['on_hand_count'] for item in on_hand_count}

        if some_on_hand:
            # Filter for recipes where you have some ingredients on hand
            user_recipes = db.execute("SELECT r.*, COUNT(distinct oi.ingredient_name) AS on_hand_count FROM recipes r JOIN relate rel ON r.recipe_id = rel.recipe_id JOIN ingredients i ON i.ingredient_id = rel.ingredient_id LEFT JOIN on_hand oi ON i.name = oi.ingredient_name AND oi.user_id = ? WHERE r.recipe_id IN ( SELECT recipe_id FROM relate JOIN ingredients ON relate.ingredient_id = ingredients.ingredient_id WHERE ingredients.name IN (SELECT ingredient_name FROM on_hand WHERE user_id = ?)) GROUP BY r.recipe_id ORDER BY COUNT(distinct oi.ingredient_name) DESC", user_id, user_id)

        elif all_on_hand:
            # Filter for recipes where you have all ingredients on hand
            user_recipes = db.execute("SELECT * FROM recipes")
            user_recipes = [recipe for recipe in user_recipes if recipe['recipe_id'] in total_count_dict and total_count_dict[recipe['recipe_id']] == on_hand_count_dict.get(recipe['recipe_id'], 0)]

        elif last_week:
            # Filter for recipes recently shopped
            user_recipes = db.execute("SELECT * FROM recipes WHERE recipe_id IN (SELECT recipe_id FROM last_shopped WHERE user_id = ? AND DATETIME(SUBSTR(date_shopped, 7, 4) || '-' || SUBSTR(date_shopped, 1, 2) || '-' || SUBSTR(date_shopped, 4, 2)) >= DATETIME('now', '-7 days')) ORDER BY name", user_id)

        elif last_month:
            # Filter for recipes that havent been shopped recently
            user_recipes = db.execute("SELECT * FROM recipes WHERE recipe_id IN (SELECT recipe_id FROM last_shopped WHERE user_id = ? AND DATETIME(SUBSTR(date_shopped, 7, 4) || '-' || SUBSTR(date_shopped, 1, 2) || '-' || SUBSTR(date_shopped, 4, 2)) <= DATETIME('now', '-30 days')) ORDER BY name", user_id)

        elif only_faves:
            # Filter for favorite recipes
            user_recipes = db.execute("SELECT * FROM recipes WHERE recipe_id IN (SELECT recipe_id FROM prefer WHERE user_id = ?)ORDER BY name", user_id)


        else:
            # No filter applied, fetch all recipes
            user_recipes = db.execute("SELECT * FROM recipes ORDER BY name")


        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 9  # Number of recipes per page

        # Modify your recipes list to include pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_recipes = user_recipes[start:end]

        # Calculate total number of pages
        total_pages = (len(user_recipes) + per_page - 1) // per_page

        # Calculate the date 7 days ago in the appropriate format
        seven_days_ago = datetime.now() - timedelta(days=7)
        formatted_date = seven_days_ago.strftime('%m-%d-%Y')

        # Execute the SQL statement to delete older ingredients
        db.execute("DELETE FROM on_hand WHERE user_id = ? AND date_updated < ?", session["user_id"], formatted_date)

        favorite_ids = db.execute("SELECT recipe_id FROM prefer WHERE user_id = ?", session["user_id"])

        # Convert the list of dictionaries to a set of IDs for easier checking
        favorite_recipe_ids = {fav['recipe_id'] for fav in favorite_ids}


        # Dictionary to hold recipe ingredients
        recipe_ingredients = {}

        on_hand_ingredients_set = {ingredient['ingredient_name'] for ingredient in ingredients_on_hand}
        # Extracting just the ingredient names into a set
        on_hand_ingredient_names = {ingredient['ingredient_name'] for ingredient in ingredients_on_hand}


        # Add a count of on-hand ingredients for each recipe and populate recipe_ingredients dictionary
        for recipe in user_recipes:
            recipe_id = recipe['recipe_id']
            ingredients = db.execute("SELECT i.name FROM ingredients i JOIN relate r ON i.ingredient_id = r.ingredient_id WHERE r.recipe_id = ? ORDER BY i.name", recipe_id)
            recipe_ingredients[recipe_id] = ingredients
            # Count how many ingredients in the recipe are on hand
            recipe['on_hand_count'] = sum(ingredient['name'] in on_hand_ingredients_set for ingredient in ingredients)


        return render_template("index.html", username=username, recipes=paginated_recipes, page=page, total_pages=total_pages, favorites=favorite_recipe_ids, recipe_ingredients=recipe_ingredients, ingredients_on_hand=ingredients_on_hand, all_ingredients=all_ingredients, title=title, no_filter=no_filter, some_on_hand=some_on_hand, all_on_hand=all_on_hand, last_week=last_week, last_month=last_month, only_faves=only_faves, on_hand_ingredient_names=on_hand_ingredient_names, last_shopped=last_shopped_dict, selected_recipes=selected_recipes)


@app.route('/test', methods=['GET'])
@login_required
def test():

    return render_template('test.html')


@app.route("/add_to_selected", methods=["POST"])
@login_required
def add_to_selected():
    recipe_id = request.form.get('recipe_id')
    if 'selected_recipes' not in session:
        session['selected_recipes'] = []
    if recipe_id and recipe_id not in session['selected_recipes']:
        session['selected_recipes'].append(recipe_id)
        return jsonify({'status': 'success', 'message': 'Recipe added'})
    return jsonify({'status': 'error', 'message': 'No recipe ID provided'})




@app.route('/remove_recipe_list', methods=['POST'])
def remove_recipe_list():
    recipe_id = request.form.get('recipe_id')
    if recipe_id and 'selected_recipes' in session:
        if recipe_id in session['selected_recipes']:
            session['selected_recipes'].remove(recipe_id)
            return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400  # Return an error status if the conditions are not met




@app.route("/add_recipe_to_session", methods=["POST"])
@login_required
def add_recipe_to_session():
    recipe_id = request.form.get('recipe_id')

    if 'selected_recipes' not in session:
        session['selected_recipes'] = []

    if recipe_id and recipe_id not in session['selected_recipes']:
        session['selected_recipes'].append(recipe_id)

    return redirect(request.referrer)




@app.route("/random_recipes", methods=["POST"])
@login_required
def random_recipes():
    user_id = session["user_id"]
    all_recipes = db.execute("SELECT * FROM recipes ORDER BY date_added DESC")
    random_recipes = random.sample(all_recipes, min(5, len(all_recipes)))

    # Update session with new random recipes
    session['selected_recipes'] = [{'id': recipe['recipe_id'], 'name': recipe['name']} for recipe in random_recipes]

    if random_recipes:
        random_recipe_ids = [recipe['id'] for recipe in session['selected_recipes']]

        # Fetch ingredients for selected recipes
        ingredients = db.execute("SELECT * FROM ingredients i JOIN relate r ON i.ingredient_id = r.ingredient_id WHERE r.recipe_id IN (?)", random_recipe_ids)
        session['selected_ingredients'] = [dict(ingredient) for ingredient in ingredients]

        # Fetch aisle information for selected ingredients and user
        selected_ingredient_ids = [ingredient['ingredient_id'] for ingredient in ingredients]

        # Construct the dynamic SQL query based on available store names
        stores = db.execute("SELECT name FROM stores")
        store_names = [store['name'] for store in stores]

        # Initialize a dictionary to store aisle information for each ingredient
        ingredient_aisles = {}

        # Iterate over store names and fetch aisle information for each store
        for store_name in store_names:
            aisle_column = f"{store_name.lower()}_aisle"
            user_aisles = db.execute("SELECT ingredient_id, {} FROM aisles WHERE ingredient_id IN ({}) AND user_id = ?".format(aisle_column, ','.join(['?'] * len(selected_ingredient_ids))), *selected_ingredient_ids, user_id)

            # Update the ingredient_aisles dictionary with aisle information for each store
            for row in user_aisles:
                ingredient_id = row['ingredient_id']
                aisle_info = row[aisle_column]
                if ingredient_id not in ingredient_aisles:
                    ingredient_aisles[ingredient_id] = {}
                ingredient_aisles[ingredient_id][store_name] = aisle_info

        # Update each ingredient with its aisle information
        for ingredient in session['selected_ingredients']:
            ingredient_id = ingredient['ingredient_id']
            aisle_info = ingredient_aisles.get(ingredient_id, {})
            ingredient.update(aisle_info)

    return redirect('shopping_list')





@app.route('/edit_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def edit_recipe(recipe_id):
    new_name = request.form.get('recipe_name').title()
    ingredients_ids = request.form.getlist('selected_ingredients[]')  # Adjusted key

    try:
        # Update recipe name
        db.execute("UPDATE recipes SET name = ? WHERE recipe_id = ?", new_name, recipe_id)

        # Update ingredient relations only if ingredients are selected
        if ingredients_ids:
            # First, remove all current ingredient relations
            db.execute("DELETE FROM relate WHERE recipe_id = ?", recipe_id)

            # Then, add new relations for each selected ingredient
            for ingredient_id in ingredients_ids:
                if ingredient_id:  # Check if ingredient_id is not empty
                    db.execute("INSERT OR REPLACE INTO relate (recipe_id, ingredient_id) VALUES (?, ?)", recipe_id, ingredient_id)

        flash("Recipe updated successfully", "success")
    except Exception as e:
        flash("An error occurred: " + str(e), "error")

    return redirect(request.referrer)






@app.route('/remove_onhand/<ingredient_name>', methods=['POST'])
@login_required
def remove_onhand(ingredient_name):
    try:
        db.execute("DELETE FROM on_hand WHERE user_id = ? AND ingredient_name = ?", session["user_id"], ingredient_name)
        flash(f"{ingredient_name} removed from on Hand", "warning")
    except Exception as e:

        flash("An error occurred", "error")
    return redirect(request.referrer)


@app.route('/remove_ingredient/<int:ingredient_id>', methods=['POST'])
@login_required
def remove_ingredient(ingredient_id):
    user_id = session["user_id"]
    try:
        db.execute("DELETE FROM relate WHERE ingredient_id = ?", ingredient_id)
        db.execute("DELETE FROM Ingredients WHERE ingredient_id = ?", ingredient_id)
        db.execute("DELETE FROM aisles WHERE ingredient_id = ?", ingredient_id)
        flash("Ingredient Deleted", "warning")
    except Exception as e:

        flash("An error occurred", "error")
    return redirect(request.referrer)



@app.route('/add_aisle/<int:ingredient_id>', methods=['POST'])
@login_required
def add_smiths_aisle(ingredient_id):
    user_id = session["user_id"]
    new_aisle = request.form.get('aisle_number').title()
    selected_store = session['selected_store']
    try:
        existing_record = db.execute("SELECT * FROM aisles WHERE user_id = ? AND ingredient_id = ?", user_id, ingredient_id)
        aisle_column = f"{selected_store.lower()}_aisle"

        if existing_record:
            # If a record exists, update the aisle information for the selected store
            db.execute("UPDATE aisles SET {} = ? WHERE user_id = ? AND ingredient_id = ?".format(aisle_column), new_aisle, user_id, ingredient_id)
        else:
            # If no record exists, insert a new one
            db.execute("INSERT OR REPLACE INTO aisles (user_id, ingredient_id, {}) VALUES (?, ?, ?)".format(aisle_column), user_id, ingredient_id, new_aisle)

        flash(f"{selected_store} Aisle Number Updated", "success")
    except Exception as e:
        flash("An error occurred: " + str(e), "error")
    return redirect(request.referrer)




@app.route('/favorite_recipe/<int:recipe_id>', methods=['POST'])
def favorite_recipe(recipe_id):
    today = date.today().strftime('%m-%d-%Y')
    try:
        db.execute("INSERT OR REPLACE INTO prefer (user_id, recipe_id, date_favorited) VALUES (?, ?, ?)", session["user_id"], recipe_id, today)
        flash("Recipe Added to Favorites", "success")
        return redirect("/")
    except Exception as e:
        # Handle exceptions, e.g., recipe already favorited
        flash("An error occurred while adding to favorites", "error")
    return redirect(request.referrer)


@app.route('/unfavorite_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def unfavorite_recipe(recipe_id):
    try:
        db.execute("DELETE FROM prefer WHERE user_id = ? AND recipe_id = ?", session["user_id"], recipe_id)
        flash("Recipe removed from favorites", "warning")
    except Exception as e:
        # Handle exceptions, e.g., recipe not in favorites
        flash("An error occurred", "error")
    return redirect(request.referrer)



@app.route('/remove_recipe/<int:recipe_id>', methods=['POST'])
def remove_recipe(recipe_id):
    db.execute("DELETE FROM relate WHERE recipe_id = ?", recipe_id)
    db.execute("DELETE FROM recipes WHERE recipe_id = ?", recipe_id)
    flash("Recipe Deleted", "warning")
    return redirect(request.referrer)





@app.route("/clear_shopping_list", methods=["POST", "GET"])
@login_required
def clear_shopping_list():
    user_id = session["user_id"]
    # Clear the session variables
    session.pop('checkbox_states', None)
    session.pop('selected_ingredients', None)
    session.pop('selected_recipes', None)
    db.execute("DELETE FROM ingredient_states WHERE user_id = ?", user_id)
    flash("Shopping list cleared.", "warning")
    return redirect("/")

@app.route("/clear_list", methods=["POST", "GET"])
@login_required
def clear_list():
    user_id = session["user_id"]
    # Clear the session variables
    session.pop('checkbox_states', None)
    session.pop('selected_ingredients', None)
    session.pop('selected_recipes', None)
    flash("Recipe List cleared.", "warning")
    return redirect("/")



@app.route("/shopping_list", methods=["GET", "POST"])
@app.route("/shopping_list/<int:list_id>", methods=["GET"])
@login_required
def shopping_list(list_id=None):
    user_id = session["user_id"]
    today = date.today().strftime('%m-%d-%Y')
    stores = db.execute("SELECT name FROM stores")
    fav_store = db.execute("SELECT store FROM fav_store WHERE user_id = ?", user_id)

    recipes = session.get('selected_recipes', [])
    recipe_names = []
    selected_recipes = session.get('selected_recipes', [])
    selected_recipe_ids = [recipe['id'] for recipe in selected_recipes if isinstance(recipe, dict) and 'id' in recipe]

    if selected_recipe_ids:
        placeholders = ', '.join(['?'] * len(selected_recipe_ids))
        recipe_names = db.execute("SELECT recipe_id, name FROM recipes WHERE recipe_id IN ({})".format(placeholders), *selected_recipe_ids)

    # Handle POST requests for creating a new shopping list
    if request.method == "POST":
        ingredients = session['selected_ingredients']

        checked_states = db.execute("SELECT ingredient_id, checked FROM ingredient_states WHERE user_id = ? AND checked = 1", user_id)
        checked_ids = [item['ingredient_id'] for item in checked_states]
        print(checked_ids)

        # Apply these checked states to the ingredients list
        for ingredient in ingredients:
            if ingredient['ingredient_id'] in checked_ids:
                ingredient['checked'] = True
            else:
                ingredient['checked'] = False

        # Fetch ingredients on hand
        ingredients_on_hand = db.execute("SELECT * FROM on_hand WHERE user_id = ?", session["user_id"])

        # Filter out ingredients that are on hand
        on_hand_ingredients = db.execute("SELECT ingredient_name FROM on_hand WHERE user_id = ?", user_id)
        on_hand_ingredient_names = [item['ingredient_name'] for item in on_hand_ingredients]

        if 'ingredient_name' in request.form:
            ingredient_name = request.form.get("ingredient_name").title()

            # Check if ingredient already on hand
            existing = db.execute("SELECT * FROM on_hand WHERE ingredient_name = ?", ingredient_name)
            if existing:
                flash("Ingredient already on hand", "error")
                return redirect("shopping_list")

            check_ingredient = db.execute("SELECT * FROM Ingredients WHERE name = ?", ingredient_name)
            if not check_ingredient:
                flash("Ingredient name must be in ingredient list", "error")
                return redirect("shopping_list")

            # Insert new ingredient into the database
            db.execute("INSERT OR REPLACE INTO on_hand (user_id, ingredient_name, date_updated) VALUES (?, ?, ?)", user_id, ingredient_name, today)
            flash("On hand Ingredient Added", "success")
            return redirect("shopping_list")

        list_name = request.form.get("listName")
        if list_name:
            list_name = list_name.title()

            # Check if a list with this name already exists
            existing_list = db.execute("SELECT list_id FROM shop_list WHERE list_name = ? AND user_id = ?", list_name, user_id)
            if existing_list:
                flash("A list with this name already exists. Please choose a different name.", "error")
                return redirect("shopping_list")

            db.execute("INSERT OR REPLACE INTO shop_list (list_name, user_id, date_created) VALUES (?, ?, ?)", list_name, user_id, today)
            result = db.execute("SELECT list_id FROM shop_list WHERE list_name = ? AND user_id = ? ORDER BY list_id DESC LIMIT 1", list_name, user_id)
            if result:
                list_id_value = result[0]['list_id']

                for ingredient in ingredients:
                    ingredient_name = ingredient['name']
                    # Check if ingredient is not on hand before adding to shopping list
                    if ingredient_name not in on_hand_ingredient_names:
                        db.execute("INSERT OR REPLACE INTO list_ids (list_id, ingredient_name) VALUES (?, ?)", list_id_value, ingredient_name)

            flash("Shopping list was saved.", "success")
            return redirect("shopping_list")
        else:
            flash("Ingredient added", "success")
            return redirect("shopping_list")

    # Handle GET requests for displaying an existing or newly created shopping list
    elif 'selected_ingredients' in session or list_id:
        list_details = None
        ingredients_info = None
        ingredients = None
        # Fetch ingredients on hand
        ingredients_on_hand = db.execute("SELECT * FROM on_hand WHERE user_id = ?", session["user_id"])

        if list_id:
            # Fetch the specific shopping list details using list_id
            list_details = db.execute("SELECT list_name, date_created FROM shop_list WHERE list_id = ?", list_id)
            if not list_details:
                flash("Shopping list not found.", "error")
                return redirect("select_recipes")

            # Fetch ingredient names for the specific list
            ingredient_names_result = db.execute("SELECT ingredient_name FROM list_ids WHERE list_id = ?", list_id)
            ingredient_names = [ingredient['ingredient_name'] for ingredient in ingredient_names_result]

            # Filter out ingredients that are on hand
            on_hand_ingredients = db.execute("SELECT ingredient_name FROM on_hand WHERE user_id = ?", user_id)
            on_hand_ingredient_names = [item['ingredient_name'] for item in on_hand_ingredients]

            # Identify which selected ingredients are on hand
            ingredients_alread_on_hand = [ingredient['ingredient_name'] for ingredient in ingredient_names_result if ingredient['ingredient_name'] in on_hand_ingredient_names]
            # Filter out ingredients that are on hand
            ingredients_to_display = [name for name in ingredient_names if name not in on_hand_ingredient_names]

            # Fetch full details of ingredients
            if ingredients_to_display:
                ingredients = db.execute("SELECT * FROM ingredients WHERE name IN (?)", ingredients_to_display)
                # Update session variables for selected ingredients and checkbox states
                session['selected_ingredients'] = [{'ingredient_id': ingredient['ingredient_id'], 'name': ingredient['name']} for ingredient in ingredients]
                checked_states = db.execute("SELECT ingredient_id, checked FROM ingredient_states WHERE user_id = ? AND checked = 1", user_id)
                checked_ids = [item['ingredient_id'] for item in checked_states]
                print(checked_ids)

                # Apply these checked states to the ingredients list
                for ingredient in ingredients:
                    if ingredient['ingredient_id'] in checked_ids:
                        ingredient['checked'] = True
                    else:
                        ingredient['checked'] = False

                session.pop('selected_recipes', None)
            return render_template("shopping_list.html", ingredients=ingredients, list_details=list_details, ingredients_on_hand=ingredients_on_hand, stores=stores, recipes=recipe_names)

        else:
            selected_ingredient_ids = [ingredient['ingredient_id'] for ingredient in session['selected_ingredients']]

            # Fetch the checked states
            checked_states = db.execute("SELECT ingredient_id FROM ingredient_states WHERE user_id = ? AND checked = 1", user_id)
            checked_ids = [item['ingredient_id'] for item in checked_states]

            # Fetch the names of all selected ingredients
            selected_ingredients_info = db.execute("SELECT ingredient_id, name FROM Ingredients WHERE ingredient_id IN (?)", selected_ingredient_ids)

            # Fetch ingredients on hand
            on_hand_ingredients = db.execute("SELECT ingredient_name FROM on_hand WHERE user_id = ?", user_id)
            on_hand_ingredient_names = [item['ingredient_name'] for item in on_hand_ingredients]

            # Identify which selected ingredients are on hand and update checked state
            ingredients_to_display = []
            for ingredient in selected_ingredients_info:
                ingredient['checked'] = ingredient['ingredient_id'] in checked_ids
                if ingredient['name'] not in on_hand_ingredient_names:
                    ingredients_to_display.append(ingredient)

            # Initialize the 'ingredients' list as an empty list
            ingredients = []

            # Fetch the latest aisle information for the remaining ingredients
            remaining_ingredient_ids = [ingredient['ingredient_id'] for ingredient in ingredients_to_display]
            if remaining_ingredient_ids:
                # Safely retrieve the selected store as a string
                selected_store = session.get('selected_store', 'Walmart')
                if isinstance(selected_store, list):
                    selected_store = selected_store['store']

                aisle_column = f"{selected_store.lower()}_aisle"

                # Query is formatted to order By length first, and then order by number. This deals with walmart aisle numbers
                aisle_query = (
                    f"SELECT i.ingredient_id, i.name, COALESCE(a.{aisle_column}, '') as aisle_value "
                    f"FROM ingredients i "
                    f"LEFT JOIN aisles a ON i.ingredient_id = a.ingredient_id "
                    f"WHERE i.ingredient_id IN ({','.join(['?']*len(remaining_ingredient_ids))}) "
                    f"ORDER BY LENGTH(aisle_value), aisle_value ASC"
                )

                rows = db.execute(aisle_query, *remaining_ingredient_ids)



                for row in rows:
                    ingredient_dict = {
                        'ingredient_id': row['ingredient_id'],
                        'name': row['name'],
                        aisle_column: row['aisle_value']
                    }

                    # Reapply checked state
                    if row['ingredient_id'] in checked_ids:
                        ingredient_dict['checked'] = True
                    else:
                        ingredient_dict['checked'] = False

                    ingredients.append(ingredient_dict)

            else:
                ingredients = []  # Initialize as an empty list when there are no remaining ingredients

            session['selected_ingredients'] = ingredients
            return render_template("shopping_list.html", ingredients=ingredients, list_details=list_details, ingredients_on_hand=ingredients_on_hand, stores=stores, recipes=recipe_names)

    else:
        flash("Please Select a Recipe", "warning")
        return redirect('/')



@app.route('/update_store', methods=['POST'])
@login_required
def update_store():
    selected_store = request.form.get('selected_store').lower()
    if selected_store:
        session['selected_store'] = selected_store
        selected_store = selected_store.title()
        flash(f"Store updated to {selected_store}", "success")
    else:
        flash("No store selected", "error")
    return redirect('shopping_list')





@app.route("/add_list_ingredient", methods=["POST"])
@login_required
def add_list_ingredient():
    if request.method == "POST":
        user_id = session["user_id"]
        ingredient_name = request.form.get("ingredient_name").title()

        existing_ingredient = any(ingredient['name'] == ingredient_name for ingredient in session['selected_ingredients'])

        # Check if the ingredient exists in the database
        ingredient_exists = db.execute("SELECT ingredient_id, name FROM Ingredients WHERE name = ?", ingredient_name)
        on_hand = db.execute("SELECT ingredient_name FROM on_hand WHERE user_id = ? AND ingredient_name = ?", user_id, ingredient_name)

        if existing_ingredient:
            flash(f"{ingredient_name} is already in your shopping list.", "warning")
        elif on_hand:
            flash(f"{ingredient_name} is already on hand", "error")
        elif not ingredient_exists:
            flash(f"{ingredient_name} was added to your shopping list AND to the database since it did not exist", "success")
            db.execute("INSERT OR REPLACE INTO Ingredients (name) VALUES (?)", ingredient_name)
            ingredient_exists = db.execute("SELECT ingredient_id, name FROM Ingredients WHERE name = ?", ingredient_name)
            session['selected_ingredients'].append(ingredient_exists[0])
        else:
            # Add the ingredient to the session
            session['selected_ingredients'].append(ingredient_exists[0])
            flash(f"{ingredient_name} added to your shopping list.", "success")

        return redirect('shopping_list')



@app.route("/add_ingredient", methods=["POST"])
@login_required
def add_ingredient():
    if request.method == "POST":
        user_id = session["user_id"]
        ingredient_name = request.form.get("ingredient_name").title()

        # Check if the ingredient exists in the database
        ingredient_exists = db.execute("SELECT ingredient_id, name FROM Ingredients WHERE name = ?", ingredient_name)

        if not ingredient_exists:
            db.execute("INSERT OR REPLACE INTO Ingredients (name) VALUES (?)", ingredient_name)
            flash(f"{ingredient_name} was added to the database", "success")
        else:
            flash(f"{ingredient_name} already exists.", "success")

        return redirect(request.referrer)



@app.route("/finish_shopping", methods=["POST"])
@login_required
def finish_shopping():
    user_id = session["user_id"]
    today = date.today().strftime('%m-%d-%Y')
    selected_ingredients = session.get('selected_ingredients', [])
    selected_recipes = session.get('selected_recipes', [])

    # Fetch checked states from the database
    checked_states = db.execute("SELECT ingredient_id FROM ingredient_states WHERE user_id = ? AND checked = 1", user_id)
    checked_ids = [item['ingredient_id'] for item in checked_states]

    # Add all checked ingredients to on_hand
    for ingredient in selected_ingredients:
        ingredient_id = ingredient['ingredient_id']
        if ingredient_id in checked_ids:
            ingredient_name = ingredient['name']
            db.execute("INSERT OR REPLACE INTO on_hand (user_id, ingredient_name, date_updated) VALUES (?, ?, ?)", user_id, ingredient_name, today)

    # Update last_shopped based on combination of checked ingredients and on_hand
    for recipe in selected_recipes:
        recipe_id = recipe['id']
        recipe_ingredient_names = db.execute("SELECT ingredients.name FROM ingredients JOIN relate ON ingredients.ingredient_id = relate.ingredient_id WHERE relate.recipe_id = ?", recipe_id)
        recipe_ingredient_names = [row['name'] for row in recipe_ingredient_names]

        # Check if all ingredients are either shopped or already on hand
        all_ingredients_covered = all(
            db.execute("SELECT ingredient_id FROM ingredients WHERE name = ?", name)[0]['ingredient_id'] in checked_ids or
            db.execute("SELECT COUNT(*) FROM on_hand WHERE user_id = ? AND ingredient_name = ?", user_id, name)[0]['COUNT(*)'] > 0
            for name in recipe_ingredient_names
        )

        if all_ingredients_covered:
            for ingredient_name in recipe_ingredient_names:
                db.execute("INSERT OR REPLACE INTO last_shopped (user_id, ingredient_name, date_shopped, recipe_id) VALUES (?, ?, ?, ?)", user_id, ingredient_name, today, recipe_id)

    # Clear the session variables and checked states
    db.execute("DELETE FROM ingredient_states WHERE user_id = ?", user_id)
    session.pop('selected_ingredients', None)
    session.pop('selected_recipes', None)

    flash("Items shopped were added to On Hand.", "success")
    return redirect("/")









@app.route('/update_checkbox_state', methods=['POST'])
def update_checkbox_state():
    data = request.json
    user_id = session["user_id"]
    ingredient_id = data['ingredientId']
    is_checked = data['checked']

    db.execute("INSERT OR REPLACE INTO ingredient_states (user_id, ingredient_id, checked) VALUES (?, ?, ?)", user_id, ingredient_id, is_checked)

    return jsonify(success=True)





@app.route('/search')
def search():
    q = request.form.getlist("ingredientSearchBox")
    if q:
        ingredient_list = db.execute("SELECT DISTINCT name, ingredient_id FROM Ingredients WHERE name LIKE ? ORDER BY name LIMIT 5", q)
    else:
        ingredient_list = []
    return render_template('search.html', ingredient_list=ingredient_list)

@app.route('/search_recipes')
def search_recipes():
    q = request.args.get('term', '')  # Get the search term from the query parameter
    if q:
        # Query the database to retrieve matching recipes (replace 'recipes' with your table name)
        recipe_list = db.execute("SELECT DISTINCT name, recipe_id FROM recipes WHERE name LIKE ? ORDER BY name LIMIT 5", f"%{q}%")
    else:
        recipe_list = []

    # Return the list of matching recipes as JSON
    return jsonify(recipe_list)


@app.route('/search_ingredients')
def search_ingredients():
    term = request.args.get('term', '')
    if term:
        ingredient_list = db.execute("SELECT DISTINCT name, ingredient_id FROM Ingredients WHERE name LIKE ? ORDER BY name", ['%' + term + '%'])
    else:
        ingredient_list = []  # Return an empty list if the search term is empty
    return jsonify(ingredient_list)


@app.route('/edit_ingredient/<int:ingredient_id>', methods=['POST'])
@login_required
def edit_ingredient(ingredient_id):
    new_name = request.form.get('ingredient_name')

    try:
        db.execute("UPDATE Ingredients SET name = ? WHERE ingredient_id = ?", new_name, ingredient_id)
        flash("Ingredient updated successfully", "success")
    except Exception as e:
        flash("An error occurred: " + str(e), "error")
    return redirect(request.referrer)



@app.route("/ingredients", methods=["GET", "POST"])
@login_required
def ingredients():
    today = date.today().strftime('%m-%d-%Y')
    user_id = session["user_id"]
    form_type = request.form.get("form_type")

    # Fetch the user's favorite store
    fav_store_result = db.execute("SELECT store FROM fav_store WHERE user_id = ?", user_id)
    fav_store = fav_store_result[0]['store'] if fav_store_result else "Walmart"

    all_ingredients = db.execute("SELECT * FROM ingredients ORDER BY name")
    ingredients_on_hand = db.execute("SELECT * FROM on_hand WHERE user_id = ?", user_id)
    stores = db.execute("SELECT name FROM stores")

    aisle_column = f"{fav_store.lower()}_aisle"
    for ingredient in all_ingredients:
        aisle_info = db.execute("SELECT {} FROM aisles WHERE user_id = ? AND ingredient_id = ?".format(aisle_column), user_id, ingredient['ingredient_id'])
        ingredient[aisle_column] = aisle_info[0][aisle_column] if aisle_info else None



    if request.method == "POST":

        if 'ingredient_name' in request.form:
            ingredient_name = request.form.get("ingredient_name").title()

            # Check if user entered ingredient name
            # (This shouldnt be needed since the name is required in the form)
            if not ingredient_name:
                flash("Ingredient name required", "error")
                return redirect("/add_recipe")

            # Check if ingredient already exists
            i_existing = db.execute("SELECT * FROM Ingredients WHERE name = ?", ingredient_name)
            if i_existing:
                flash("Ingredient already exists", "error")
                return redirect("/ingredients")
            else:
                db.execute("INSERT OR REPLACE INTO Ingredients (name) VALUES (?)", ingredient_name)
                flash("New Ingredient Added", "success")

            # After adding the ingredient, reload the same page
            return redirect("/ingredients")


        if form_type == "fav_store":
                store_name = request.form.get("store_name")
                new_store = request.form.get("new_store")
                if new_store:
                    exists = db.execute("SELECT * FROM stores WHERE name = ?", new_store)
                    if exists:
                        flash("Store already exists", "error")
                        return redirect("/ingredients")
                    else:
                        db.execute("INSERT OR REPLACE INTO stores (name) VALUES (?)", new_store)
                        # Format the new column name (e.g., "newstore_aisle")
                        new_aisle_column = f"{new_store.lower()}_aisle"

                        # Alter the ingredients table to add the new column
                        alter_query = f"ALTER TABLE ingredients ADD COLUMN {new_aisle_column} TEXT"
                        db.execute(alter_query)
                    store_name = new_store
                    session['selected_store'] = store_name

                # Update the user's favorite store before performing the redirect
                db.execute("INSERT OR REPLACE INTO fav_store (user_id, store) VALUES (?, ?)", user_id, store_name)
                session['selected_store'] = store_name

                # Fetch the aisles for the new favorite store
                aisle_column = f"{store_name.lower()}_aisle"
                for ingredient in all_ingredients:
                    aisle_info = db.execute("SELECT {} FROM aisles WHERE user_id = ? AND ingredient_id = ?".format(aisle_column), user_id, ingredient['ingredient_id'])
                    ingredient[aisle_column] = aisle_info[0][aisle_column] if aisle_info else None

                flash("Favorite Store Updated", "success")
                return redirect("/ingredients")


    else:

        return render_template("ingredients.html", all_ingredients=all_ingredients, ingredients_on_hand=ingredients_on_hand, fav_store=fav_store, stores=stores)




@app.route("/add_recipe", methods=["GET", "POST"])
@login_required
def add_recipe():
    ingredient_list = []
    today = date.today().strftime('%m-%d-%Y')
    user_info = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = user_info[0]['username'] if user_info else ''
    all_ingredients = db.execute("SELECT * FROM ingredients ORDER BY name")
    ingredients_on_hand = db.execute("SELECT * FROM on_hand WHERE user_id = ?", session["user_id"])


    if request.method == "POST":

        if 'ingredient_name' in request.form:
            ingredient_name = request.form.get("ingredient_name").title()

            # Check if user entered ingredient name
            # (This shouldnt be needed since the name is required in the form)
            if not ingredient_name:
                flash("Ingredient name required", "error")
                return redirect("/add_recipe")

            # Check if ingredient already exists
            i_existing = db.execute("SELECT * FROM Ingredients WHERE name = ?", ingredient_name)
            if i_existing:
                flash("Ingredient already exists", "error")
                return redirect("/add_recipe")

            else:
                db.execute("INSERT OR REPLACE INTO Ingredients (name) VALUES (?)", ingredient_name)



            flash("New Ingredient Added", "success")

            # After adding the ingredient, reload the same page
            return redirect("/add_recipe")

        # Else, handle recipe addition
        recipe_name = request.form.get("recipe_name").title()
        selected_ingredients = request.form.getlist("selected_ingredients[]")

        # Check if recipe already exists
        r_existing = db.execute("SELECT * FROM recipes WHERE name = ?", recipe_name)
        if r_existing:
            flash("Recipe already exists", "error")
            return redirect("/add_recipe")
        else:
            # Insert new recipe into recipe table
            db.execute("INSERT OR REPLACE INTO recipes (name, added_by, date_added) VALUES (?, ?, ?)", recipe_name, username, today)
            # grab the recipe_id
            recipe_id = db.execute("SELECT recipe_id FROM recipes WHERE name = ?", recipe_name)
            if recipe_id and len(recipe_id) > 0:
                recipe_id_value = recipe_id[0]['recipe_id']
            else:
                flash("Error fetching recipe ID", "error")
                return redirect("/add_recipe")

            # process the ingredients
            for ingredient_id in selected_ingredients:
                # Convert ingredient_id to int if it's a string
                ingredient_id_value = int(ingredient_id)
                # Execute the query with both values as separate elements in a tuple
                db.execute("INSERT OR REPLACE INTO relate (recipe_id, ingredient_id) VALUES (?, ?)", recipe_id_value, ingredient_id_value)

            flash("New Recipe Added", "success")
            return redirect("/add_recipe")



    if request.method == "GET":
        return render_template("add_recipe.html", ingredient_list=ingredient_list, all_ingredients=all_ingredients, ingredients_on_hand=ingredients_on_hand)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username").lower():
            flash("must provide username", "error")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password", "error")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username").lower())

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            flash("invalid username and/or password", "error")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    today = date.today().strftime('%m-%d-%Y')
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username").lower():
            flash("must provide username", "error")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password", "error")
            return render_template("register.html")


        # Ensure they confirm their password
        elif not request.form.get("confirmation"):
            flash("must confirm password", "error")
            return render_template("register.html")

        # Ensure passwords matched
        elif request.form.get("confirmation") != request.form.get("password"):
            flash("passwords don't match", "error")
            return render_template("register.html")

        # Ensure username doesn't already exist
        elif db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username")):
            flash("username already taken", "error")
            return render_template("register.html")

        password = request.form.get("password")

        # Hash password
        newusername = request.form.get("username").lower()
        newhash = generate_password_hash(password)

        # Attempt to add new user
        try:
            new_user_id = db.execute(
                "INSERT OR REPLACE INTO users (username, hash, created_on) VALUES (?, ?, ?)", newusername, newhash, today)
        except:
            flash("Registration error", "error")
            return render_template("register.html")

        # Remember which user has logged in
        session["user_id"] = new_user_id

        # Redirect user to home page
        return redirect("/")

    else:
        # User reached route via GET (as by clicking a link or via redirect)
        return render_template("register.html")


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    today = date.today().strftime('%m-%d-%Y')
    user_id = session["user_id"]
    user_info = db.execute("SELECT username, created_on, email FROM users WHERE id = ?", session["user_id"])
    username = user_info[0]['username'] if user_info else ''
    created_on = user_info[0]['created_on'] if user_info else ''
    email = user_info[0]['email'] if user_info else ''
    shopping_lists = db.execute("SELECT * FROM shop_list WHERE user_id = ?", session["user_id"])
    favorites = db.execute("SELECT r.*, p.date_favorited FROM recipes r INNER JOIN prefer p ON r.recipe_id = p.recipe_id WHERE p.user_id = ?", user_id)
    ingredients_on_hand = db.execute("SELECT * FROM on_hand WHERE user_id = ?", session["user_id"])
    fav_store = db.execute("SELECT store FROM fav_store WHERE user_id = ?", user_id)
    stores = db.execute("SELECT name FROM stores")

    if request.method == "GET":
        # Calculate the date 7 days ago in the appropriate format
        seven_days_ago = datetime.now() - timedelta(days=7)
        formatted_date = seven_days_ago.strftime('%m-%d-%Y')

        # Execute the SQL statement to delete older ingredients
        db.execute("DELETE FROM on_hand WHERE user_id = ? AND date_updated < ?", session["user_id"], formatted_date)


        # Display account page
        return render_template("account.html", username=username, created_on=created_on, email=email, shopping_lists=shopping_lists, favorites=favorites, ingredients_on_hand=ingredients_on_hand, fav_store=fav_store, stores=stores)

    else:
        # Calculate the date 7 days ago in the appropriate format
        seven_days_ago = datetime.now() - timedelta(days=7)
        formatted_date = seven_days_ago.strftime('%m-%d-%Y')

        # Execute the SQL statement to delete older ingredients
        db.execute("DELETE FROM on_hand WHERE user_id = ? AND date_updated < ?", session["user_id"], formatted_date)


        form_type = request.form.get("form_type")

        if form_type == "add_ingredient":
            ingredient_name = request.form.get("ingredient_name").title()

            # Check if ingredient already on hand
            existing = db.execute("SELECT * FROM on_hand WHERE ingredient_name = ?", ingredient_name)
            if existing:
                flash("Ingredient already on hand", "error")
                return redirect("/account")

            check_ingredient = db.execute("SELECT * FROM Ingredients WHERE name = ?", ingredient_name)
            if not check_ingredient:
                flash("Ingredient name must be in ingredient list", "error")
                return redirect("/account")

            # Insert new ingredient into the database
            db.execute("INSERT OR REPLACE INTO on_hand (user_id, ingredient_name, date_updated) VALUES (?, ?, ?)", user_id, ingredient_name, today)
            flash("On hand Ingredient Added", "success")

            # After adding the ingredient, reload the same page
            return redirect("/account")

        if form_type == "add_email":
            new_email = request.form.get("new_email")
            db.execute("UPDATE users SET email = ? WHERE id = ?", new_email, user_id)
            flash("Email Successfully Added", "success")
            return redirect("/account")

        if form_type == "update_email":
            new_email = request.form.get("new_email")
            db.execute("UPDATE users SET email = ? WHERE id = ?", new_email, user_id)
            flash("Email Successfully Changed", "success")
            return redirect("/account")

        if form_type == "change_password":
            # Check if the password change form was submitted
            if 'oldpass' in request.form:
                oldpass = request.form.get("oldpass")
                newpass = request.form.get("newpass")
                confirm = request.form.get("confirm")

                # Validate form input
                if not oldpass or not newpass or not confirm:
                    flash("Missing old or new password", "error")
                    return redirect("/account")

                # Retrieve user's current password hash
                hash = db.execute("SELECT hash FROM users WHERE id = ?", user_id)
                hash = hash[0]['hash']

                # Verify old password
                if not check_password_hash(hash, oldpass):
                    flash("Old password incorrect", "error")
                    return redirect("/account")

                # Check if new passwords match
                if newpass != confirm:
                    flash("New passwords do not match", "error")
                    return redirect("/account")

                # Hash new password and update database
                new_hash = generate_password_hash(newpass)
                db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, user_id)
                flash("Password successfully changed", "success")

        if form_type == "fav_store":
            store_name = request.form.get("store_name")
            new_store = request.form.get("new_store")
            if new_store:
                exists = db.execute("SELECT * FROM stores WHERE name = ?", new_store)
                if exists:
                    flash("Store already exists", "error")
                    return redirect("/account")
                else:
                    db.execute("INSERT OR REPLACE INTO stores (name) VALUES (?)", new_store)
                    # Format the new column name (e.g., "newstore_aisle")
                    new_aisle_column = f"{new_store.lower()}_aisle"

                    # Alter the ingredients table to add the new column
                    alter_query = f"ALTER TABLE ingredients ADD COLUMN {new_aisle_column} TEXT"
                    db.execute(alter_query)
                store_name = new_store

            # Update the user's favorite store
            db.execute("INSERT OR REPLACE INTO fav_store (user_id, store) VALUES (?, ?)", user_id, store_name)

            flash("Favorite Store Updated", "success")
            return redirect("/account")


        # Redirect to account page after processing
        return render_template("account.html", username=username, created_on=created_on, email=email, shopping_lists=shopping_lists, favorites=favorites, ingredients_on_hand=ingredients_on_hand, fav_store=fav_store, stores=stores)


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        form_type = request.form.get("form_type")
        username = request.form.get("username").lower()
        newpass = request.form.get("newpass")
        confirm = request.form.get("confirm")

        if form_type == "forgot_password":
            user = db.execute("SELECT * FROM users WHERE username = ?", username)

            # Ensure username exists and password is correct
            if len(user) != 1:
                flash("invalid username", "error")
                return render_template("login.html")

            if not newpass or not confirm:
                flash("Need to enter a new password and confirm", "error")
                return redirect("/reset_password")

            if newpass != confirm:
                flash("New passwords do not match", "error")
                return redirect("/reset_password")

            # Query for user_id using the provided username
            user_id_result = db.execute("SELECT id FROM users WHERE username = ?", username)
            if user_id_result:
                user_id = user_id_result[0]["id"]

                # Hash new password and update database
                new_hash = generate_password_hash(newpass)
                db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, user_id)

                # Remember which user has logged in
                session["user_id"] = user_id
                flash("Password successfully changed", "success")
                return redirect("/")
            else:
                flash("Username not found", "error")
                return redirect("/reset_password")

    return render_template("reset_password.html")




@app.route('/remove_list/<int:list_id>', methods=['POST'])
def remove_list(list_id):
    # Code to remove the shopping list from the database
    db.execute("DELETE FROM list_ids WHERE list_id = ?", list_id)
    db.execute("DELETE FROM shop_list WHERE list_id = ?", list_id)
    # You might also need to delete related entries in other tables
    flash("Shopping List Deleted", "warning")
    return redirect("/account")

@app.route('/remove_favorite/<int:recipe_id>', methods=['POST'])
def remove_favorite(recipe_id):
    try:
        db.execute("DELETE FROM prefer WHERE user_id = ? AND recipe_id = ?", session["user_id"], recipe_id)
        flash("Recipe removed from favorites", "success")
    except Exception as e:
        # Handle exceptions, e.g., recipe not in favorites
        flash("An error occurred", "error")
    return redirect("/account")


if __name__ == '__main__':
	app.run(debug=True)
