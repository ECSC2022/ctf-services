### Building and running the checker

Run the application (from `/dist`)
```
docker-compose up
```

Run the checker for one tick (from `/checker/checker2`)
```
TICK=0 docker-compose up
```

This will do the following:

- call place_flag for the current tick
- call check_service
- call check_flag for up to 5 previous ticks (one invocation per tick)

To test that checking previous ticks works, call the checker with increasing tick numbers:
```
TICK=1 docker-compose up # checked ticks: 0, 1
TICK=2 docker-compose up # checked ticks: 0, 1, 2
TICK=3 docker-compose up # checked ticks: 0, 1, 2, 3
TICK=4 docker-compose up # checked ticks: 0, 1, 2, 3, 4
TICK=5 docker-compose up # checked ticks: 0, 1, 2, 3, 4, 5
TICK=6 docker-compose up # checked ticks: 1, 2, 3, 4, 5, 6
...
```
