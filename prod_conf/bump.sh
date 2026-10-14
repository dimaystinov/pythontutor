#!/bin/zsh

SCRIPT_SOURCE=$(/bin/readlink -f ${0%/*}) # from http://stackoverflow.com/a/14728194
cd $SCRIPT_SOURCE

GITREPO_URL=`git config --get remote.origin.url`

echo 'Загрузка во временную папку...'
sudo -upythontutor git clone -q --progress --depth=1 --branch=production $GITREPO_URL .bump-tmp
cd .bump-tmp

echo 'bump_pre.sh:'
$SCRIPT_SOURCE/bump_pre.sh
if [[ ! $? -eq 0 ]]; then
        echo '  неуспешно :('
        cd ..

        STATUS=1
else
        echo 'Всё ок, вроде :)'
        cd ..

        echo 'Остановка сервера...'
        supervisorctl stop pythontutor > /dev/null
        echo 'Обновление продакшна...'
        sudo -upythontutor git pull -q --progress
        echo 'Запуск сервера...'
        supervisorctl start pythontutor > /dev/null

        STATUS=0
fi

echo 'Удаление временной папки...'
rm -r .bump-tmp

if [[ $STATUS -eq 0 ]]; then
        echo 'Всё :)'
fi

exit $STATUS
