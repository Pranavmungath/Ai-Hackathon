$venvName = ".venv"
python -m venv ("..\" + $venvName)
$path = "..\" + $venvName + "\Scripts\activate.ps1"
Invoke-Expression $path
python -m pip install --upgrade pip
python -m pip install -r ..\requirements.txt