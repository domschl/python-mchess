def set_keyboard_valid(self, vals):
        self.kbd_moves = []
        if vals != None:
            for v in vals:
                self.kbd_moves.append(vals[v])

    def kdb_event_worker_thread(self, appque, log, std_in):
        while self.kdb_thread_active:
            cmd = ""
            try:
                # cmd = input()
                # with open(std_in) as inp:
                cmd = std_in.readline().strip()
            except Exception as e:
                log.info("Exception in input() {}".format(e))
                time.sleep(1.0)
            if cmd == "":
                continue
            log.debug("keyboard: <{}>".format(cmd))
            if len(cmd) >= 1:
                if cmd in self.kbd_moves:
                    self.kbd_moves = []
                    appque.put(
                        {'move': {'uci': cmd, 'actor': 'keyboard'}})
                elif cmd == 'n':
                    log.debug('requesting new game')
                    appque.put({'new game': '', 'actor': 'keyboard'})
                elif cmd == 'b':
                    log.debug('move back')
                    appque.put({'back': '', 'actor': 'keyboard'})
                elif cmd == 'c':
                    log.debug('change board orientation')
                    appque.put(
                        {'turn eboard orientation': '', 'actor': 'keyboard'})
                elif cmd == 'a':
                    log.debug('analyze')
                    appque.put({'analyze': '', 'actor': 'keyboard'})
                elif cmd == 'ab':
                    log.debug('analyze black')
                    appque.put({'analyze': 'black', 'actor': 'keyboard'})
                elif cmd == 'aw':
                    log.debug('analyze white')
                    appque.put({'analyze': 'white', 'actor': 'keyboard'})
                elif cmd == 'e':
                    log.debug('board encoding switch')
                    appque.put({'encoding': '', 'actor': 'keyboard'})
                elif cmd[:2] == 'l ':
                    log.debug('level')
                    movetime = float(cmd[2:])
                    appque.put({'level': '', 'movetime': movetime})
                elif cmd[:2] == 'm ':
                    log.debug('max ply look-ahead display')
                    n = int(cmd[2:])
                    appque.put({'max_ply': n})
                elif cmd == 'p':
                    log.debug('position')
                    appque.put({'position': '', 'actor': 'keyboard'})
                elif cmd == 'g':
                    log.debug('go')
                    appque.put({'go': 'current', 'actor': 'keyboard'})
                elif cmd == 'gw':
                    log.debug('go')
                    appque.put({'go': 'white', 'actor': 'keyboard'})
                elif cmd == 'gb':
                    log.debug('go, black')
                    appque.put({'go': 'black', 'actor': 'keyboard'})
                elif cmd == 'w':
                    appque.put({'write_prefs': ''})
                elif cmd[:2] == 'h ':
                    log.debug('show analysis for n plys (max 4) on board.')
                    ply = int(cmd[2:])
                    if ply < 0:
                        ply = 0
                    if ply > 4:
                        ply = 4
                    appque.put({'hint': '', 'ply': ply})

                elif cmd == 's':
                    log.debug('stop')
                    appque.put({'stop': '', 'actor': 'keyboard'})
                elif cmd[:4] == 'fen ':
                    appque.put({'fen': cmd[4:], 'actor': 'keyboard'})
                elif cmd == 'help':
                    log.info(
                        'a - analyze current position, ab: analyze black, aw: analyses white')
                    log.info(
                        'c - change cable orientation (eboard cable left/right')
                    log.info('b - take back move')
                    log.info('g - go, current player (default white)')
                    log.info('gw - go, force white move')
                    log.info('gb - go, force black move')
                    log.info('h <ply> - show hints for <ply> levels on board')
                    log.info('l <n> - level: engine think-time in sec (float)')
                    log.info('m <n> - max plys shown during look-ahead')
                    log.info('n - new game')
                    log.info('p - import eboard position')
                    log.info('s - stop')
                    log.info('w - write current prefences as default')
                    log.info('e2e4 - valid move')
                else:
                    log.info(
                        'Unknown keyboard cmd <{}>, enter "help" for a list of valid commands.'.format(cmd))

    def keyboard_handler(self):
        self.kdb_thread_active = True
        self.kbd_event_thread = threading.Thread(
            target=self.kdb_event_worker_thread, args=(self.appque, self.log, sys.stdin))
        self.kbd_event_thread.setDaemon(True)
        self.kbd_event_thread.start()
