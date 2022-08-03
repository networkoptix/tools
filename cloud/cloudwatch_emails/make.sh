#!/bin/bash

function build_frontend() {
    pushd frontend
        echo "cleaning build"
        [ -d "build" ] && rm -rf build
        echo "installing packages"
        npm install
        echo "building app"
        npm run build
        echo "cleaning files"
        mv build/static/* build
        rm -rf build/static
        [ -d "../server/static" ] && rm -rf ../server/static
        mkdir ../server/static
        echo "moving files to server"
        mv build/* ../server/static
    popd
}

function install_or_activate_pip () {
    if [ ! -d "env" ]
    then
        echo "virtual env not found creating it"
        python3 -m venv env
        if [ ! -d "./env/Scripts/activate" ]
        then
            . ./env/bin/activate
        else
            . ./env/Scripts/activate
        fi
        pip install -r server/requirements.txt
    else
        if [ ! -d "./env/Scripts/activate" ]
        then
            . ./env/bin/activate
        else
            . ./env/Scripts/activate
        fi
    fi
    echo "Virtual env has been activated"
}


for command in $@
do
    case "$command" in
        build_app)
            install_or_activate_pip
            build_frontend
            ;;
        run)
            install_or_activate_pip
            pushd server
                gunicorn server:app -w 2 --threads 2 -b 0.0.0.0:8000
            popd
            ;;
        run_local)
            install_or_activate_pip
            pushd server
                export FLASK_APP='server.py'
                flask run
            popd
            ;;
        *)
        echo Usage: app "[build_app|run|run_local]"
    esac
done
