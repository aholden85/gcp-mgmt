"""
BEFORE RUNNING:
---------------
1. If not already done, enable the relevant API and check the quota for
   your project at
   https://console.developers.google.com/apis/dashboard
2. This sample uses Application Default Credentials for authentication.
   If not already done, install the gcloud CLI from
   https://cloud.google.com/sdk and run
   `gcloud auth application-default login`.
   For more information, see
   https://developers.google.com/identity/protocols/application-default-credentials
3. Install the Python client library for Google APIs by running
   `pip install --upgrade google-api-python-client`
"""

from googleapiclient import discovery

# init a dictionary of api resources
api_resources = {}

"""
API Service-related functions.
"""
def init_api(serviceName, version='v1'):
    """Initialises an instance of an API resource.

    Args:
        serviceName: string, the name of the required API service.
        version: string, the version of the API service.
    """
    # TODO: add in ability to pass credentials
    global api_resources
    if serviceName not in api_resources:
        api_resources[serviceName] = discovery.build(serviceName=serviceName, version=version)

def get_api_state(projectNumber, serviceName):
    """Returns the state of an API service.

    Args:
        projectNumber: string, the number of the target project.
        serviceName: string, the name of the target API service.
    """
    init_api(serviceName='serviceusage')
    return api_resources['serviceusage'].services().get(name='projects/{}/services/{}.googleapis.com'.format(projectNumber,serviceName)).execute()['state']

def set_api_state(projectNumber, serviceName, serviceState):
    """Sets the state of an API service.

    Args:
        projectNumber: string, the number of the target project.
        serviceName: string, the name of the target API service.
        serviceState: string, the desired state of the API service.
    
    Issues:
        "Billing must be enabled for activation of service '[compute.googleapis.com, compute.googleapis.com, compute.googleapis.com]' in project 'XXXXXXXXXXXX' to proceed."
    """
    init_api(serviceName='serviceusage')
    if serviceState == 'DISABLED':
        return api_resources['serviceusage'].services().disable(name='projects/{}/services/{}.googleapis.com'.format(projectNumber,serviceName)).execute()
    elif serviceState == 'ENABLED':
        return api_resources['serviceusage'].services().enable(name='projects/{}/services/{}.googleapis.com'.format(projectNumber,serviceName)).execute()
    else:
        raise ValueError('Desired service state must be either ENABLED or DISABLED, not {}.'.format(serviceState))



"""
Basic API functions.
"""
def list_projects():
    init_api(serviceName='cloudresourcemanager')
    return api_resources['cloudresourcemanager'].projects().list().execute()

def list_compute(projectId):
    init_api(serviceName='compute')
    return api_resources['compute'].instances().aggregatedList(project=projectId).execute()

def list_static_ips(projectId):
    init_api(serviceName='compute')
    return api_resources['compute'].addresses().aggregatedList(project=projectId).execute()

def list_buckets(projectId):
    init_api(serviceName='storage')
    return api_resources['storage'].buckets().list(project=projectId).execute()

def list_billing():
    init_api(serviceName='cloudbilling')
    return api_resources['cloudbilling'].list().execute()

def list_sinks(parent):
    """Lists the logging sinks for the specified resource.

    Args:
        The parent resource whose sinks are to be listed:
        
        "projects/[PROJECT_ID]"
        "organizations/[ORGANIZATION_ID]"
        "billingAccounts/[BILLING_ACCOUNT_ID]"
        "folders/[FOLDER_ID]"
    """
    init_api(serviceName='logging', version='v2')
    return api_resources['logging'].sinks().list(parent=parent).execute()

def list_uptime_check_ips():
    init_api(serviceName='monitoring', version='v3')
    return api_resources['monitoring'].uptimeCheckIps().list().execute()

def list_uptime_check_configs(projectId):
    init_api(serviceName='monitoring', version='v3')
    return api_resources['monitoring'].projects().uptimeCheckConfigs().list(parent='projects/{}'.format(projectId)).execute()

def test_iam(projectId):
    init_api(serviceName='cloudresourcemanager')

    permissions = {
        "permissions": [
            "storage.buckets.list"
        ]
    }

    return api_resources['cloudresourcemanager'].projects().testIamPermissions(resource=projectId, body=permissions).execute()



"""
Functions built upon the basic API functions.
These have specific outcomes, such as getting pricing or compliance details.
"""
def get_external_ip_pricing():
    # https://cloud.google.com/compute/network-pricing#ipaddress
    prices_per_hour={
        'RESERVING': 0.014,
        'RESERVED': 0.014,
        'IN_USE': 0.004,
    }

    with open("output.csv", "w") as csv_export:
        csv_export.write('projectId,region,name,address,status,pph\n')
        
        projects = list_projects()['projects']
        for active_project in (project for project in projects if project['lifecycleState'] == 'ACTIVE'):
            if get_api_state(active_project['projectNumber'],'compute') == 'ENABLED':
                regions = list_static_ips(active_project['projectId'])['items']
                for regionKey in regions:
                    region = regions[regionKey]
                    if 'addresses' in region:
                        for valid_address in (address for address in region['addresses'] if address['addressType'] == 'EXTERNAL'):
                            csv_export.write('{},{},{},{},{},{}\n'.format(active_project['projectId'],regionKey,valid_address['name'],valid_address['address'],valid_address['status'],prices_per_hour[valid_address['status']]))
                    else:
                        pass
            else:
                pass

def get_all_buckets():
    projects = list_projects()['projects']
    for active_project in (project for project in projects if project['lifecycleState'] == 'ACTIVE'):
        if get_api_state(active_project['projectNumber'],'compute') == 'ENABLED':
            for bucket in list_buckets(active_project['projectId'])['items']:
                print ('{} is in {}\n'.format(bucket['name'],bucket['location']))

def get_all_compute_ip_addresses():
    projects = list_projects()['projects']
    for active_project in (project for project in projects if project['lifecycleState'] == 'ACTIVE'):
        projectId=active_project['projectId']
        if get_api_state(active_project['projectNumber'],'compute') == 'ENABLED':
            zones = list_compute(active_project['projectId'])
            for zone in zones['items']:
                if 'instances' in zones['items'][zone]:
                    for instance in zones['items'][zone]['instances']:
                        print(instance['name'],instance['networkInterfaces'][0]['networkIP'],sep=',')
