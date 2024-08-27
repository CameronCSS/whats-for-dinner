# What's 4 Dinner

#### [Video Demo](<https://www.youtube.com/watch?v=OztMCgm2H9A>)

> [!IMPORTANT] 
> #### You can create an account and try the BETA [HERE](https://whats4dinner.app)
> #### <sup>*Note: I may shut off registrations if it gets too busy*</sup>

### Preview 

![image](https://github.com/user-attachments/assets/7a31e98a-eeb9-460d-8456-184c76facbc5)


## Overview

We’ve all faced the age-old question: *"What's for dinner?"* Every single day we have to check the fridge, check your pantry, decide what we want, and finally make a shopping list because we realize there's no food in the house.

**Then after all that you still have to go and actually SHOP. UGHH!!**

### My Solution

**What's 4 Dinner** is a web app designed to simplify both meal planning and shopping:

- **Random Recipe Selector**: When you can't decide what to cook, let the app pick recipes for you.
- **Streamlined Shopping**: Map your store's aisles once, and your shopping list will be automatically sorted for a easier shopping experience.


#### Why Manual Aisle Mapping?

I considered using local data and scraping store websites to auto-update aisle information. However, this made the entire project much more complicated and was in all sorts of grey areas since I needed to get your local data (zip code) AND scrape data from big companies that do not like you scraping anything from their websites.

## Features

- **Ingredient Tracker**: Keep track of what you have at home. Ingredients are auto-deleted after 7 days, so no need for manual removal.
- **Favorite Recipes**: Save and manage your favorite recipes.
- **Recipe Sorted by What you have**: Find recipes based on the ingredients you have on hand.
- **Recipe Rotation**: Sort recipes by the last time you shopped for them to avoid repeating meals too often.
- **Random Recipe Generator**: Get 5 random recipes and a shopping list that excludes ingredients you already have.
- **Shopping List Quick Add**: Easily add items to your shopping list and receive a warning if you already have them on hand.
- **Custom Ingredients & Recipes**: Add your own ingredients and recipes. The app includes about 50 recipes and hundreds of ingredients.
- **Saved Shopping Lists**: Save and reuse shopping lists for future trips. The app will update your list based on what ingredients you have on hand.
- **Store-Specific Aisle Mapping**: Add and track multiple stores' aisles, specific to your shopping habits.


----

## Future Wants

- **Automated Aisle Information**: Ideally, auto-add aisle details from chosen stores (though this is currently a low priority).
- **Barcode Scanning**: Scan items to quickly update your 'On Hand' inventory.
- **Recipe Inventory**: View recipes based on ingredients you’ve purchased, for convenience.
- **Aisle Sorting**: Add the ability to sort by aisle numbers, based on store layout.
- **Recipe Search**: Improve the search functionality for easier recipe discovery.
- **Enhanced Design**: Update the app’s visual elements for a more appealing look.
- **Usage Statistics**: Add a page to view your most frequently shopped recipes and ingredients.
- **Expiration Dates**: Optionally track ingredient expiration dates and set reminders (currently considered overkill).

## Technical Details

- **Languages Used**: Python (~1300 lines), JavaScript (~500 lines), HTML (~400 lines), SQL (~50 lines).
- **Database**: Local SQLite database with 13 tables to manage user data and app information.
- **Frameworks & Libraries**: Flask is the main python Framework doing most of the interaction and heavy lifting (besides straight code)
- **Development Time**: I've spend over 100 hours programming it. To be fair, a lot of the early days where when I was lost and had NO idea what I was doing. Even now it could probably use a fresh start since its very messy and not well optimized.
- **Design**: A majority of the app and look is built upon bootstrap coding. I have gone in and customized a few things. But for the most part its just basic bootstrap. (This definitely needs to be updated to be what I envisioned)

---

#### Description expanded
I started with the flask framework we learned when doing the CS50 course.
Infact I am using a lot of the example code and cs50 library.
The further I got and the more I learned I just expanded on each idea and worked on that one thing until it worked correctly.
I have never programmed a full app like this, only little things that are like 50 lines of code MAX. I am not a developer, but I imagine this is sort of what the development cycle looks like.

- Start with base code
- Add a feature
- Add a new feature and make it work with everything else you currently have
- Add complexity and security
- Go back and add more features

This is basically what I did. Except I did it all over the course of a few months. It has been almost a YEAR since I originally wrote this code. I commented and documented almost everything, which I'm glad I did.
But that doesnt really help much when coming back to such a huge wall of code and having no idea what certain chunks do (Other than some of the comments I added)

Luckily CS50 lets you carry over from one year, so even though everything else was finished in 2023 and THIS isnt being submitted until 2024. I can still finish up the certification.


### Why the hold up?

Why has it taken me so long to submit a FINAL assignement so I can get my certificate??

I originally wanted to put this on pause because I was at the limit of my current coding skill. I wanted to study code AND CSS / html and come back to it when I could make it run smoother / faster. I also wanted to wait until I could come back and make it look 100x better.
it looks ok, but its not at a place I am happy with just yet.
