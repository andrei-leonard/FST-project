import threading, queue, time, random, socket, errno, os


# add random delays to emulate bad connection
FUZZ = True

def fuzz():
    if FUZZ:
        time.sleep(random.random())


filename_queue = queue.Queue()

def file_manager():
    ' daemon that should manage list of files to be signed '

    # all the files we want to send to be signed
    file_list = []

    while True:
        # get the filename from the queue
        filename, evt = filename_queue.get()

        #print('file_manager got: ', filename)

        # add the filename to a separate list
        file_list.append((filename, evt))


        # if more files were received use them
        if not filename_queue.empty():
            # mark current queue element as done
            filename_queue.task_done()
            continue

        #print('goto sign_queue with one batch of files', file_list)

        # add all the filenames to the signing queue
        sign_queue.put(file_list)

        # mark current queue element as done
        filename_queue.task_done()

        # clear the filelist
        file_list = []

t = threading.Thread(target=file_manager)
t.daemon = True
t.start()
del t


sign_queue = queue.Queue()

def sign_manager():
    ' (-theoretical-) exclusive rights to the files we want to sign '
    while True:
        # one task as a list
        flist = sign_queue.get()

        print('generating the FST')

        header = ""
        with open("header.fst", "rb") as file:
            header = file.read()

        footer = ""
        with open("footer.fst", "rb") as file:
            footer = file.read()


        with open("signfiles.fst", "wb") as file:
            file.write(header);

            for filename in flist:
                print(filename)
                out = '1 "{}"'.format(filename)
                print(out)
                file.write(out)

            file.write(footer);

        #print('sign manager got the list ', flist)
        fuzz()

        os.system('notepad')

        #for filename in flist:
            #print("sign_manager got: ", filename)
            #todo - create .fst file

        #execute the command

        #perform signing job
        fuzz()

        #finish
        fuzz()

        #print('finished signing the list ', flist)

        for filename, evt in flist:
            #print('prepare for worker_queue:', filename)
            evt.set()

        # finish the one task
        sign_queue.task_done()

        # undo the generated FST
        os.remove('signfiles.fst')

t = threading.Thread(target=sign_manager)
t.daemon = True
t.start()
del t

#worker_queue = queue.Queue()

def worker(evt, sock, addr):
    ' job is to receive & send back the result '

    try:
        # Receive filename and filesize 
        data = sock.recv(2048)

        # Check received data length
        if not data:
            print("No data received")
            raise Error('No data received')

        filename, filesize = (data.decode("utf-8")).split(" ")
        print("received - filename:{0}, size:{1}".format(filename, filesize))
        
        isDuplicate = False
        originalFilename = ""

        if os.path.exists(filename) == True:
            # new filename in order to make it unique
            sock.send("filename is already processing ...")
            originalFilename = filename
            filename = filename + "_" + random.random()
            print('change the filename to: ' + filename)
            isDuplicate = True

        # Download file
        with open(filename, "wb") as file:
            start_time = time.time()
            data = sock.recv(2048)
            total = len(data)
            file.write(data)
            elapsed_time = 0
            while total < int(filesize) and elapsed_time <= 30:
                data = sock.recv(2048)
                total += len(data)
                file.write(data)
                elapsed_time = time.time() - start_time
                print("{0:.02f}".format((total / float(filesize)) * 100) + "% done in {0:.05f} sec.".format(elapsed_time))

        if elapsed_time > 30:
            #UndoDirChanges(str(addr))
            raise Error('30 sec receive timeout reached')

        print( ("Download of {} done!").format(filename) )

        while isDuplicate == True:
            # wait 5 sec for it to be signed
            sock.send('wait 5 sec')
            time.sleep(5)
            if os.path.exists(originalFilename) == False:
                os.rename(filename, originalFilename)
                isDuplicate = False
                break
            else:
                sock.send('filename is still processing ...')

        # start file signing process
        filename_queue.put((filename, evt))

        # block until file was signed
        evt.wait()

        print(('worker sent {} and event was received').format(filename))

        filename = filename + '.p7s'

        # Get file size of the target file
        filesize = os.path.getsize(filename)

        print('signed filename:{0}, filesize:{1}'.format(filename, filesize))

        # Check the file size before sending any data
        if filesize == 0:
            raise Error('Missing signed file')

        time.sleep(0.2)

        with open(filename, "rb") as file:
            start_time = time.time()
            bytesToSend = file.read(2048)
            sock.send(bytesToSend)
            total = len(bytesToSend)
            elapsed_time = 0
            while bytesToSend != "" and elapsed_time <= 30 and total < filesize:
                bytesToSend = file.read(2048)
                sock.send(bytesToSend)
                total += len(bytesToSend)
                elapsed_time = time.time() - start_time
                print("{0:.02f}".format((total / float(filesize)) * 100) + "% done in {0:.05f} sec.".format(elapsed_time))

        if elapsed_time > 30:
            UndoDirChanges(dir_path)
            raise Error('30 sec send timeout reached')

        print( ("Upload of {} done!").format(filename) )

        # Socket shutdown
        sock.shutdown(socket.SHUT_RDWR)

        # Disconnect from server
        sock.close()

        # Remove filename
        os.remove(filename)

        #send
        fuzz()
    except:
        pass

def Main():

    # Server IP and port ( IPv4 )
    host = ''           # Symbolic name meaning all available interfaces
    port = 50007        # Arbitrary non-privileged port

    # Setup socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to address.
    sock.bind((host, port))

    # Listen for connections with maximum number of queued connections (system-dependent)
    sock.listen(5)

    print("\n------------------------------")
    print("|    FST - Server started    |")
    print("|  Listening on port: 50007  |")
    print("------------------------------\n")

    while True:
        try:
            
            # Accept a connection
            conn, addr = sock.accept()

            print("< Connected client IP: " + str(addr) + " >")
            
            evt = threading.Event()

            # Thread constructor
            t = threading.Thread(target=worker, args=(evt, conn, addr))
            
            # Start the thread’s activity
            t.start()

        except KeyboardInterrupt:
            raise

    # Disconnect from server
    sock.close()

if __name__ == '__main__':
    Main()