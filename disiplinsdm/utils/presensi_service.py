import requests
from oauth2_provider.models import get_application_model

Application = get_application_model()

def get_flask_bridge_credentials(app_name="Attlog_Bridge_Worker"):
    Application = get_application_model()
    try:
        app = Application.objects.get(name=app_name)
        return {
            "client_id": app.client_id,
            "client_secret": app.client_secret,
        }
    except Application.DoesNotExist:
        return None
    
    
def get_data_from_flask():
    # 1. Minta Token ke Diri Sendiri (SIMADU)
    client_id = get_flask_bridge_credentials().get('client_id')
    client_secret = get_flask_bridge_credentials().get('client_secret')
    token_url = "http://localhost:8000/o/token/"
    credentials = (client_id, client_secret)

    token_res = requests.post(
        token_url, 
        data={'grant_type': 'client_credentials'},
        auth=credentials
    )
    access_token = token_res.json().get('access_token')

    # 2. Gunakan Token untuk ambil data ke Flask
    flask_url = "http://localhost:5000/api/v1/unsynced"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(flask_url, headers=headers)
    return response.json()