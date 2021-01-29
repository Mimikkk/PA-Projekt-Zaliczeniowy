from requests import request

# a = request("GET", "https://ekursy.put.poznan.pl/mod/quiz/view.php?id=571364")
# print(a.text)
from app import App

if __name__ == '__main__':
    App().run_server(debug=False)
