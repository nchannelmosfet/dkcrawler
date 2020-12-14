.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m jupyter nbextension enable --py widgetsnbextension
.\venv\Scripts\python.exe -m jupyter labextension install @jupyter-widgets/jupyterlab-manager
.\venv\Scripts\python.exe -m jupyter lab build