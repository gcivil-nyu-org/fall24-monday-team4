# RoutePals

## Master:
[![Build Status](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4.svg?branch=master)](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4?branch=master) [![Coverage Status](https://coveralls.io/repos/github/gcivil-nyu-org/fall24-monday-team4/badge.svg?branch=master)](https://coveralls.io/github/gcivil-nyu-org/fall24-monday-team4?branch=master)

## Develop:
[![Build Status](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4.svg?branch=develop)](https://app.travis-ci.com/gcivil-nyu-org/fall24-monday-team4?branch=develop)
[![Coverage Status](https://coveralls.io/repos/github/gcivil-nyu-org/fall24-monday-team4/badge.svg?branch=develop)](https://coveralls.io/github/gcivil-nyu-org/fall24-monday-team4?branch=develop)

## Description:
RoutePals is a web application focused on enhancing personal safety during travel in New York City, specifically designed for NYU students. It connects individuals traveling along similar routes, operating on the "safety in numbers" principle. Users can create trips, match with companions going in the same direction, and travel together. The app features real-time location sharing, an emergency alert system, and companion verification through NYU credentials. Key safety features include a panic button with emergency support monitoring, family member notifications, and secure group chat functionality.

The platform requires NYU email verification and document submission for account authentication, ensuring a trusted user base. It's particularly useful for students traveling at night or through unfamiliar neighborhoods, offering them a safer way to commute by connecting with fellow verified NYU students.

## Video Demo:
[![Video](https://github.com/user-attachments/assets/2347575d-dc9b-4136-8c6f-fcd18883e73d)](https://youtu.be/tHrZaLRgloI)

## Built With:
- Framework: Django
- Frontend: HTML/CSS (Django Templates), Javascript, Bootstrap
- API Services: Pusher.com
- Database: AWS RDS (PostgreSQL), AWS S3
- CI/CD: AWS Elastic Beanstalk, Travis CI, Coveralls.io (Coverage)

## Main Features:
- Authentication with NYU Email verification
- Document-based User Verification System 
- Trip Creation with Route Planning
- Companion Matching System
- Custom Search Filters for Matching
- Real-time Location Tracking
- Live Chat System with Message Encryption
- Emergency Alert System with Panic Button
- Emergency Support System
- Family Member Email Notifications
- User Profiles with Social Media Integration
- Admin Management System
- Map Integration with Route Display
- Real-time Trip Status Updates
- Trip History and Archives
- Multi-user Trip Completion Voting

## Source Links
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

### Run Application
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
``` 

## Contributing:
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Contact:
Shashank datta Bezgam (sb9477@nyu.edu)  
Jeffrey Wong (jw4186@nyu.edu)  
Jacqueline Ji (xj235@nyu.edu)  
Samara Augustin (sa8242@nyu.edu)  
Idan Lau (yl9727@nyu.edu)
