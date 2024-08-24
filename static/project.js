$.noConflict();


function filterIngredients(recipeId = '') {
    var searchTerm = document.getElementById("ingredientSearchBox" + (recipeId ? recipeId : '')).value;

    // Make an AJAX request to the server
    fetch('/search_ingredients?term=' + encodeURIComponent(searchTerm))
        .then(response => response.json())
        .then(data => {
            updateIngredientList(data, recipeId);
        })
        .catch(error => {
            console.error('Error fetching ingredients:', error);
        });
}




function updateIngredientList(data, recipeId = '') {
    var ingredientList = document.getElementById("ingredientList" + (recipeId ? recipeId : ''));
    ingredientList.innerHTML = ''; // Clear current list

    // Populate the list with the results
    data.forEach(ingredient => {
        var li = document.createElement("li");
        li.className = "list-group-item";
        li.setAttribute("data-ingredient-id", ingredient.ingredient_id);
        li.textContent = ingredient.name;
        li.onclick = function() { selectIngredient(this, recipeId); };
        ingredientList.appendChild(li);
    });
}





function selectIngredient(element, recipeId = '') {
    var ingredientId = element.getAttribute('data-ingredient-id');
    var ingredientName = element.textContent;

    // Determine the IDs based on whether recipeId is provided
    var formId = recipeId ? "recipeForm" + recipeId : "addRecipeForm";
    var selectedListId = recipeId ? "selectedIngredientsList" + recipeId : "selectedIngredientsList";

    var form = document.getElementById(formId);
    var selectedList = document.getElementById(selectedListId);

    if (!form || !selectedList) {
        console.error('Form or selected list not found');
        return;
    }

    // Create a hidden input for the form submission
    var input = document.createElement("input");
    input.type = "hidden";
    input.name = "selected_ingredients[]";
    input.value = ingredientId;

    // Append hidden input to the correct form
    form.appendChild(input);

    // Add to the selected list
    var li = document.createElement("li");
    li.textContent = ingredientName;
    li.className = "list-group-item";
    li.setAttribute("data-ingredient-id", ingredientId);

    // Create a remove button
    var removeButton = document.createElement("button");
    removeButton.textContent = "Remove";
    removeButton.className = "btn btn-danger btn-sm";
    removeButton.onclick = function() {
        selectedList.removeChild(li);
        form.removeChild(input);
    };

    li.appendChild(removeButton);
    selectedList.appendChild(li);

    // Clear the search box and ingredient list
    if (recipeId) {
        document.getElementById("ingredientSearchBox" + recipeId).value = '';
        document.getElementById("ingredientList" + recipeId).innerHTML = '';
    } else {
        document.getElementById("ingredientSearchBox").value = '';
        document.getElementById("ingredientList").innerHTML = '';
    }
}



// Call filterIngredients initially to load the ingredient list
filterIngredients();


function prepareModal(actionUrl, aisleColumn, ingredientId, ingredientName, recipeName, recipeId) {
    // Determine whether it's for editing an ingredient or setting aisle
    if (actionUrl.includes('edit_ingredient')) {
        // Set up for editing an ingredient
        document.getElementById('ingredientForm').action = actionUrl;
        document.getElementById('editIngredientName').value = ingredientName;
        document.getElementById('ingredientId').value = ingredientId;
    } else if (actionUrl.includes('add_aisle')) {
        // Set up for adding or editing an aisle
        document.getElementById('aisleForm').action = actionUrl;
        document.getElementById('ingredientId').value = ingredientId;
        document.getElementById('aisleModalLabel').innerText = ingredientName + ' Aisle Number';
    } else if (actionUrl.includes('edit_recipe')) {
        // Set up for editing a recipe
        document.getElementById('recipeForm').action = actionUrl;
        document.getElementById('editRecipeName').value = recipeName;
        document.getElementById('recipeId').value = recipeId;
    }
}




  function submitShoppingList() {
    var listName = document.getElementById('uniqueListName').value;

    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'listName';
    input.value = listName;
    document.getElementById('shoppingListForm').appendChild(input);

    document.getElementById('shoppingListForm').submit();
}


const selectStoreDropdown = document.getElementById('selected_store');

selectStoreDropdown.addEventListener('change', function () {
    const selectedStore = this.value;
    const hiddenStoreInput = document.getElementById('selected_store_hidden');

    // Update the hidden input with the selected store value
    hiddenStoreInput.value = selectedStore;
});


function updateCheckboxState(checkbox, ingredientId) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/update_checkbox_state", true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify({
        ingredientId: ingredientId,
        checked: checkbox.checked
    }));
}




// Function helper for confirmation box
function setFormAction(url, message) {
    document.getElementById('confirmBtn').onclick = function() {
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        form.style.display = 'none';
        document.body.appendChild(form);
        form.submit();
    };
    document.getElementById('confirmationMessage').textContent = message;
}




function showLogoutConfirmation() {
    // Set the confirmation message
    document.getElementById('logoutconfirmationMessage').textContent = "Are you sure you want to log out?";

    // Change the action for the confirm button to redirect to logout URL
    document.getElementById('logoutconfirmBtn').onclick = function() {
        window.location.href = '/logout';
    };

    // Show the modal
    jQuery('#logoutconfirmationModal').modal('show');
}





// Function to toggle Question mark Note
function togglePopup(element) {
    var popup = element.querySelector(".popup-modal");
    if (popup.style.display === "none" || !popup.style.display) {
        popup.style.display = "block";
    } else {
        popup.style.display = "none";
    }
}


// --------------------------------------------------- //



// ---  Functions to handle adding Recipes to the Live list --- //

// Recipe "Select" buttons
const selectButtons = document.querySelectorAll('.select-recipe-btn');

const selectedRecipesList = document.getElementById('selectedRecipesList');

// Add a click event listener to each "Select" button
selectButtons.forEach(button => {
  button.addEventListener('click', () => {
    const recipeId = button.getAttribute('data-recipe-id');

    const listItem = document.createElement('li');
    listItem.innerText = `Recipe ID: ${recipeId}`;

    selectedRecipesList.appendChild(listItem);
  });
});



function addRecipeToSessionAndUI(recipeId, recipeName) {
    // Update UI
    updateSelectedRecipesListUI(recipeId, recipeName);

    // AJAX call to update session
    addRecipeToSession(recipeId, recipeName);
}

function addRecipeToSession(recipeId, recipeName) {
    jQuery.ajax({
        type: "POST",
        url: "/",
        data: {
            recipe_id: recipeId,
            recipe_name: recipeName
        },
        success: function(response) {
            // Handle success
        },
        error: function(error) {
            console.log("Error: " + error);
        }
    });
}


function updateSelectedRecipesListUI(recipeId, recipeName) {
    var listItemHtml = '<li class="list-group-item" data-recipe-id="' + recipeId + '">' +
                       recipeName +
                       ' <button class="btn btn-danger btn-sm" onclick="removeRecipe(this, \'' + recipeId + '\')">Remove</button></li>';
    jQuery('#selectedRecipesList').append(listItemHtml);
    jQuery('#selectedRecipesHeader').text('Selected Recipes');
    jQuery('#recipeForm button[type="submit"]').show();
}




// BOTH of the above function are needed for correct features I want



// Function to remove Selected Recipes from the Live List
function removeRecipe(buttonElement, recipeId) {
    // Remove the list item from the UI
    var li = buttonElement.closest('li');
    var selectedList = document.getElementById("selectedRecipesList");
    selectedList.removeChild(li);
    // Remove the list item for the recipe
    jQuery(buttonElement).closest('li[data-recipe-id="' + recipeId + '"]').remove();

    // Check if the list is now empty
    if (jQuery('#selectedRecipesList').find('li').length === 0) {
        jQuery('#selectedRecipesHeader').text('Select recipes to create a shopping list');
        jQuery('#recipeForm button[type="submit"]').hide();
    }

    jQuery.ajax({
        type: "POST",
        url: "/remove_recipe_list", // This should be the route in your Flask app that handles recipe removal
        data: { recipe_id: recipeId },
        success: function(response) {
            console.log("Recipe removed from session");
        },
        error: function(error) {
            console.log("Error: " + error);
        }
    });
}



// Adding a new ingredient and reloading the shopping list
document.getElementById('addIngredientForm').addEventListener('submit', function(event) {
    event.preventDefault();
    var ingredientName = document.getElementById('newIngredientName').value;

    jQuery.ajax({
        type: "POST",
        url: "/add_list_ingredient",
        data: { ingredient_name: ingredientName },
        success: function(response) {
            jQuery('#addIngredientModal').modal('hide');

            reloadShoppingList();
        },
        error: function(error) {
            console.log("Error: " + error);
        }
    });
});


// Function to reload the shopping list (Used in the above function)
function reloadShoppingList() {
    location.reload();
}




// --------------------------------------------------- //




// ---  Functions to handle Recipe favorites Stars --- //


// Function to toggle favorite recipe Stars
function toggleFavorite(recipeId, recipeName, element) {
    if (element.classList.contains('favorite')) {
        // Currently a favorite, so unfavorite it
        unfavoriteRecipe(recipeId, element);
    } else {
        // Not a favorite, so favorite it
        favoriteRecipe(recipeId, element);
    }
}


function favoriteRecipe(recipeId, element) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/favorite_recipe/' + recipeId, true);

    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            element.innerHTML = '&#9829;'; // Filled heart with scaling
            element.classList.add('favorite');
        }
    };
    xhr.send();
}

function unfavoriteRecipe(recipeId, element) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/unfavorite_recipe/' + recipeId, true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            element.innerHTML = '&#9825;'; // Empty heart
            element.classList.remove('favorite');
        }
    };
    xhr.send();
}


function prepareFormAndSubmit(recipeId) {
    var form = document.getElementById("recipeForm" + recipeId); // Dynamically target the form
    var selectedIngredients = document.querySelectorAll("#selectedIngredientsList .list-group-item");

    selectedIngredients.forEach(ingredient => {
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = "selected_ingredients[]";
        input.value = ingredient.getAttribute('data-ingredient-id');
        form.appendChild(input);
    });

    form.submit();
}



document.addEventListener('DOMContentLoaded', function() {
    var sidebar = document.getElementById('sidebar');
    var toggleButton = document.getElementById('sidebarToggle');

    toggleButton.addEventListener('click', function() {
        var isVisible = sidebar.style.display === 'block';
        sidebar.style.display = isVisible ? 'none' : 'block';
        toggleButton.innerHTML = isVisible ? '❯' : '❮'; // Change chevron direction
    });
});

