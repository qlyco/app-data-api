# app-data-api

## Overview

This is a simple REST api that aims to provide some essential app data needed
for some apps.

## Features

- Get a random seed from the server
  - Supports hourly, daily, weekly, monthly, and yearly seeds.
  - Useful for features that require standardized random seed, such as daily
  challenges
- Get the current server time
  - Server time returned is based on Asia/Singapore timezone.
  - Useful for implementing a daily reset system, or for a single source of
  truth for timers.
- Get version number of specific apps
  - Useful for notifying user about a version update

## Deployment

1. Create a [Supabase](https://supabase.com) & [Fly.io](https://fly.io) account.
2. Create a new app in Fly, and a new project in Supabase.
3. Add the following secrets:
  - ```CACHE_PATH```: Path to the ```sqlite``` database file used as a cache.
  - ```SUPABASE_URL```: The Supabase project URL.
  - ```SUPABASE_ANON_KEY```: The anon key for your Supabase project.
4. In your Supabase project, add the ```app_details``` table with this schema:
  - ```name``` TEXT PRIMARY KEY
  - ```version``` TEXT
  - ```changelog``` TEXT
  - ```updated_on``` TIMESTAMP
  - ```release_date``` TIMESTAMP
5. Deploy your the API to Fly.