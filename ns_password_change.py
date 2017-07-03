import logging
import getpass
import requests
from datetime import datetime

# Configure logger.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Gather/set statics.
username = input("Username: ")
password = getpass.getpass()

nsip = input("Enter the SDX IP: ")

new_pass = input("Enter the new password: ")

profile_name = input("Enter the new profile name: ")

base_url = 'https://{}/nitro/v2/config/'.format(nsip)

# Creates the session used to connect.
try:
    s = requests.Session()
    s.verify = False
    s.stream = True
    s.trust_env = False

    s.headers.update({'ContentType': 'application/json'})

    login = {'login': {'username': username, 'password': password}}

    logger.info('Making login request to: {}'.format(base_url))
    login_request = s.post(base_url+'login', json=login)
except:
    raise

# If the session was created, continue.
if s.cookies:

    # Make sure that the admin profile doesn't already exist so that we can append something if it does.
    logger.info('Checking to see if admin profile already exists.')

    ns_device_profile_exists = False
    today = datetime.now()
    desired_profile_name = profile_name + '-{}'.format(today.strftime('%Y%m%d'))
    i = 1

    while not ns_device_profile_exists:
        logger.debug('Checking for device profile: {}'.format(desired_profile_name))
        profile = s.get(base_url + 'ns_device_profile?filter=name:{}'.format(desired_profile_name)).json()
        if len(profile['ns_device_profile']) == 0:
            logger.debug('Profile does not exist.')
            ns_device_profile_exists = True
        else:
            desired_profile_name = desired_profile_name + '-' + str(i)
            i = i + 1
            logger.debug('Profile already exists!  Renamed to {}'.format(desired_profile_name))

    new_device_profile = {'ns_device_profile': {'name': desired_profile_name, 'username': 'nsroot', 'password': new_pass}}

    response = s.post(base_url + 'ns_device_profile?action=add', json=new_device_profile)
    print(response.status_code)
# If the admin profile was successful, switch the devices over to that profile.
    if response.status_code == requests.codes.ok:

        logger.info('Retrieving VPX instances.')
        vpx_instances = s.get(base_url + 'ns', timeout=2).json()

        for vpx in vpx_instances['ns']:
            update_pw_payload = {'ns': {'id': vpx['id'], 'profile_name': desired_profile_name, 'username': 'entnet', 'password': new_pass}}
            response = s.put(base_url + 'ns/' + vpx['id'], json=update_pw_payload).json()
            if response['errorcode'] == 0:
                logger.info('Successfully changed on {}'.format(vpx['name']))
            else:
                logger.info('Failed to change on {}.  Reason: {}'.format(vpx['name'], response['message']))

    s.close()
else:
    logger.info('Login failed.  Error code is: {}'.format(login_request.json()))
