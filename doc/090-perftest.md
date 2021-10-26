# Perf testing

To perform perftesting (mostly for DB usage) two scripts have been created.

- [perfTest.py](../perfTest.py)
- [webHookSmashTest.py](../webHookSmashTest.py)

## [perfTest.py](../perfTest.py)

### Script description

This script will create N user entry.  
They will all be connected to the tests services BlackHole and WebHookSavage.  
If the tests services codes aren't present the script will not works.

### Dev usage

```bash
sudo docker exec -it hub-decathlon_web_1 python perfTest.py --nbUser N
```

**N** must be a positive integer.

## [webHookSmashTest.py](../webHookSmashTest.py)

### Script description

This script will create a webhook notification for each user connected to WebHookSavage.  
The list of user is itterated only once.  
These webhook notification must been queued/un-queued by the HUB (Working front / Scheduler / Workers).

### Dev usage

```bash
sudo docker exec -it hub-decathlon_web_1 python webHookSmashTest.py
```
