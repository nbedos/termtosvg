# Purpouse
Simplify process of building app

# Usage

Building image:

```docker build -f Dockerfile-build -t termtosvg-builder```

Running image: 

```docker run --rm -v /VOLUMEPATH:/builded termtosvg-builder build```

After compile it will be avalaible in volume /VOLUMEPATH

```docker run --rm -v /VOLUMEPATH:/builded termtosvg-builder MAKECOMMAND```

Command above will pass MAKECOMMAND to make, so user can actually also put here tests, examples etc

