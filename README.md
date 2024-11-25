# routepals

## Description
A brief description of your project goes here.

## Build Status
### Master Branch
[![Build Status](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4.svg?branch=master)](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4?branch=master)
### Develop Branch
[![Build Status](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4.svg?branch=develop)](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4?branch=develop)

## Coverage
### Master Branch
[![Coverage Status](https://coveralls.io/repos/github/gcivil-nyu-org/fall24-monday-team4/badge.svg?branch=master)](https://coveralls.io/github/gcivil-nyu-org/fall24-monday-team4?branch=master)
### Develop Branch
[![Coverage Status](https://coveralls.io/repos/github/gcivil-nyu-org/fall24-monday-team4/badge.svg?branch=develop)](https://coveralls.io/github/gcivil-nyu-org/fall24-monday-team4?branch=develop)

## Links
### Production (master)
1. [AWS EB Site](https://routepals-prod-env.us-west-2.elasticbeanstalk.com)
2. [GitHub Source](https://github.com/gcivil-nyu-org/fall24-monday-team4/tree/master)

### Development (develop)
1. [AWS EB Site](https://routepals-dev-env.us-west-2.elasticbeanstalk.com)
2. [GitHub Source](https://github.com/gcivil-nyu-org/fall24-monday-team4/tree/develop)

### Travis CICD Dashboard
[Travis CICD Dashboard](https://app.travis-ci.com/github/gcivil-nyu-org/fall24-monday-team4/branches?serverType=git)

### Coveralls Code Coverage Dashboard
[Coveralls Dashboard](https://coveralls.io/github/gcivil-nyu-org/fall24-monday-team4)

## Setup Instructions

### Prerequisites
- Ensure that Python is installed on your system. You can download it [here](https://www.python.org/downloads/).


### Commands

```bash
# Clone the repository
git clone https://github.com/gcivil-nyu-org/fall24-monday-team4.git
cd ./fall24-monday-team4

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

# Make migrations
python manage.py makemigrations

# Run migrations
python manage.py migrate

# Run local server
python manage.py runserver

# Deactivate the virtual environment
deactivate

# Update the requirements.txt if new packages are installed
pip freeze > requirements.txt
