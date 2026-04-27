import requests
import config

BASE_URL = "https://api.curseforge.com/v1"
HEADERS = {
    'Accept': 'application/json',
    'x-api-key': config.CURSEFORGE_API_KEY
}

def get_mod_info(mod_id):
    """Получает детальную информацию о моде по его ID."""
    url = f"{BASE_URL}/mods/{mod_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()['data']
    return None

def get_latest_file(mod_id, game_version=None):
    """Получает последний файл мода (опционально для версии игры)."""
    url = f"{BASE_URL}/mods/{mod_id}/files"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        files = response.json()['data']
        if files:
            # Сортируем по дате создания, чтобы взять самый новый
            files.sort(key=lambda x: x['fileDate'], reverse=True)
            return files[0]
    return None

def search_mod(query):
    """Ищет мод по названию."""
    params = {'gameId': 432, 'searchFilter': query, 'pageSize': 1}
    response = requests.get(f"{BASE_URL}/mods/search", headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()['data']
        return data[0] if data else None
    return None
