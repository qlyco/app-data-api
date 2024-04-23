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

## Upcoming Features

- Get version number of specific apps
  - Useful for notifying user about a version update