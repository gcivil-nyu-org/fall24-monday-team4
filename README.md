# routepals

## Description
A brief description of your project goes here.

## Build Status
[![Build Status](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4.svg?branch=develop)](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4)

## Coverage
With `&&service`

[![Coverage Status](https://coveralls.io/repos/github/shashankdatta/swe-app1/badge.svg?branch=main&&service=github)](https://coveralls.io/github/shashankdatta/swe-app1?branch=main)

Without `&&service`

[![Coverage Status](https://coveralls.io/repos/github/shashankdatta/swe-app1/badge.svg?branch=main)](https://coveralls.io/github/shashankdatta/swe-app1?branch=main)

Without `branch` and `&&service`

[![Coverage Status](https://coveralls.io/repos/github/shashankdatta/swe-app1/badge.svg)](https://coveralls.io/github/shashankdatta/swe-app1?branch=main)

## Links
1. [AWS EB Site](http://django-mysite-dev.us-west-2.elasticbeanstalk.com/polls)
2. [GitHub Source](https://github.com/shashankdatta/swe-app1.git)
2. [Travis CI Dashboard](https://app.travis-ci.com/github/shashankdatta/swe-app1/branches?serverType=git)

## Setup Instructions

### Prerequisites
- Ensure that Python is installed on your system. You can download it [here](https://www.python.org/downloads/).

### Commands

```bash
# Clone the repository
git clone <repository-url>
cd <project-directory>

# For Windows: Create virtual environment
python -m venv venv

# For macOS/Linux: Create virtual environment
python3 -m venv venv

# For Windows: Activate virtual environment
.\venv\Scripts\activate

# For macOS/Linux: Activate virtual environment
source venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Run the project
python <your_main_script.py>

# Deactivate the virtual environment
deactivate

# Update the requirements.txt if new packages are installed
pip freeze > requirements.txt
