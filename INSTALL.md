## Install
Once the source code is ready, we can start to setup the environment and run the test script. 
### Environment setup
This artifact requires Python 3.7+, pip, npm, and Node.js 12+. If you are using Ubuntu 18.04 or 20.04, you can simply install them by running:

```shell
$ ./ubuntu_setup.sh
```

At the same time, other Unix-like operating systems(e.g., macOS) are also supported, to install Python, simply follow the instructions from the official website of [Python](https://www.python.org/downloads/). For Node.js, please check out the official website of [Node.js](https://nodejs.org/en/) to install it.

After the packages are successfully installed, you can setup the environment by **cd** into the source code folder and run

```shell
$ ./install.sh
```

The script **install.sh** will install a list of required Python and Nodejs dependencies. Once finished, the environment is setup and we are ready to go.

### Verify the installation
You can run the script **odgen\_test.py** to verify the installation. The command is:

```shell
$ python3 ./odgen_test.py
```

If the environment is successfully set up, you should be able to see the tests are finished without errors. The end of the outputs should be like: 

```shell
Ran 3 tests in XXXs

OK
```
