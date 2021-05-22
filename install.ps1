New-Item -ItemType Directory -Force -Path '.\DK_Data_By_URLs'
New-Item -ItemType Directory -Force -Path '.\DK_Data_By_Vendor'

py -3 -m pip install virtualenv
py -3 -m virtualenv venv

# download and unzip Geckodriver for using selenium webdriver with Firefox
$gecko_path = '.\src\geckodriver.exe'
if ((Test-Path -path $gecko_path)) {
	Remove-Item $gecko_path
}
if (!(Test-Path -path $gecko_path)) {
	$gecko_url = "https://github.com/mozilla/geckodriver/releases/download/v0.29.1/geckodriver-v0.29.1-win64.zip"
	$gecko_zip = '.\src\geckodriver.zip'
	Invoke-WebRequest -Uri $gecko_url -OutFile $gecko_zip
	Expand-Archive -Path $gecko_zip -DestinationPath '.\src'
	Remove-Item $gecko_zip
}

.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m jupyter nbextension enable --py widgetsnbextension
.\venv\Scripts\python.exe -m jupyter labextension install @jupyter-widgets/jupyterlab-manager
.\venv\Scripts\python.exe -m jupyter lab build

$items_to_hide = ".\src", ".\.gitignore", ".\.git", "requirements.txt", ".\venv", ".\idea", ".\.ipynb_checkpoints"
foreach ($path in $items_to_hide) {
	if (Test-Path -path $path){
		$item = Get-Item $path -Force
		$item.attributes="Hidden"
	}
}