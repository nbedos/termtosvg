# Purpouse
Docker container that allow user to use containerized termtosvg

# Usage

Building image:

```docker build -t termtosvg .```

Running image: 

```docker run --rm -v $(pwd)/save:/save -it termtosvg /save/tosave.svg```


Command above will expose volume inside /save to currentUserDir/save, and if you will add additional command /save/tosave.svg at the end of docker run command - it will save here output command


