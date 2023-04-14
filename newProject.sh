

projectName=$1

if [ -z "$1" ]
 then
 echo "Enter the project name: "
 read projectInputName
 projectName=$projectInputName
fi

mkdir $projectName
echo "$projectName project has been created." 

templatePath="./template_for_fetchers"

mkdir $projectName/src
cp -R $templatePath/src $projectName
cp -R $templatePath/loader $projectName
cp -R $templatePath/__template_for_fetchers.py $projectName
cp -R $templatePath/template_for_fetchers.py $projectName

cd $projectName/loader

python3 initial_load.py
