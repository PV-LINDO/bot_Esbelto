"""
Some example strategies for people who want to create a custom, homemade bot.
And some handy classes to extend
"""

import chess
from chess.engine import PlayResult
from engine_wrapper import EngineWrapper
import time
from threading import Thread

class FillerEngine:
    """
    Not meant to be an actual engine.

    This is only used to provide the property "self.engine"
    in "MinimalEngine" which extends "EngineWrapper"
    """
    def __init__(self, main_engine, name=None):
        self.id = {
            "name": name
        }
        self.name = name
        self.main_engine = main_engine

    def __getattr__(self, method_name):
        main_engine = self.main_engine

        def method(*args, **kwargs):
            nonlocal main_engine
            nonlocal method_name
            return main_engine.notify(method_name, *args, **kwargs)

        return method

class MinimalEngine(EngineWrapper):
    """
    Subclass this to prevent a few random errors

    Even though MinimalEngine extends EngineWrapper,
    you don't have to actually wrap an engine.

    At minimum, just implement `search`,
    however you can also change other methods like
    `notify`, `first_search`, `get_time_control`, etc.
    """
    def __init__(self, commands, options, stderr, draw_or_resign, name=None, **popen_args):
        super().__init__(options, draw_or_resign)

        self.engine_name = self.__class__.__name__ if name is None else name

        self.engine = FillerEngine(self, name=self.name)
        self.engine.id = {
            "name": self.engine_name
        }

    def search(self, board, time_limit, ponder, draw_offered):
        """
        The method to be implemented in your homemade engine

        NOTE: This method must return an instance of "chess.engine.PlayResult"
        """
        raise NotImplementedError("The search method is not implemented")

    def notify(self, method_name, *args, **kwargs):
        """
        The EngineWrapper class sometimes calls methods on "self.engine".
        "self.engine" is a filler property that notifies <self> 
        whenever an attribute is called.

        Nothing happens unless the main engine does something.

        Simply put, the following code is equivalent
        self.engine.<method_name>(<*args>, <**kwargs>)
        self.notify(<method_name>, <*args>, <**kwargs>)
        """
        pass


class esbelto(MinimalEngine):

    def __init__(self, commands, options, stderr, draw_or_resign, name=None, **popen_args):
        super().__init__(commands, options, stderr, draw_or_resign, name, **popen_args)

        self.transposition = {}
        self.evaltt = {}
        self.temptt = {}
        self.tempeval = {}
        self.cleanse = False

        self.knightmap = [
          -10, -10, -10, -10, -10, -10, -10, -10,
          -10, -10,  -5,   0,   0,  -5,  -5, -10,
          -10,  -5,  10,   0,   0,  10,  -5, -10,
           -5,   0,  10,  20,  20,  10,   0,  -5,
           -5,   0,  10,  20,  20,  10,   0,  -5,
          -10,  -5,  10,   0,   0,  10,  -5, -10,
          -10, -10,  -5,   0,   0,  -5, -10, -10,
          -10, -10, -10, -10, -10, -10, -10, -10 ]

        self.kingmap = [
              10,  18,  20, -50,   0, -50,  30,  27, 
              0,  -5,   0, -80,-100, -80,   5,   5, 
            -10, -20, -50, -50, -50, -50, -20, -10,
            -5,  -20,  -5, -10, -10,  -5, -20,  -5,
            -5,    0,   5,  10,  10,   5,   0,  -5,
             10,  20,  50,  50,  50,  50,  20,  10,
              0,   5,  10,  80, 100,  80,   0, -10,
             -10, -18, -20,  50,   0,  50, -30, -27, 
        ]

        print('init')

    def search (self, game, maxtime, ponder, *args):
        self.abort_ponder = True
        self.abort = False
        self.resigned = False
        self.shouldabort = False
        self.movenumber = game.fullmove_number
        self.move = chess.Move.null()
        self.cutoff = 0
        self.nodes = 0
        t1 = Thread(target = self.iterativedeepening, args = (game, maxtime, *args))
        t2 = Thread(target = self.timemanegement, args = (game, maxtime, *args), daemon = True)
        t2.start()
        t1.start()
        t1.join()

        if ponder and self.resigned == False:
            t3 = Thread(target = self.ponder, args = (self.move, game, *args), daemon = True)
            self.abort_ponder = False
            t3.start()

        print('beta cutoffs:', self.cutoff)
        print('nodes:', self.nodes)

        if (self.move != chess.Move.null()):
            return PlayResult(self.move, None, resigned = self.resigned)
        else:
            print('null')
            return PlayResult(list(game.legal_moves)[0], None)       

    def iterativedeepening (self, game, *args):
   
        while self.cleanse:
            print('.')
            time.sleep(0.1)

        maxdepth = 9
        bestmove = chess.Move.null()
        depth = 0

        if len(list(game.legal_moves)) == 1:
            print ('ID => onlymove')
            self.move = list(game.legal_moves)[0]
            return

        while (depth <= maxdepth):

            movelist = self.ordermoves (game, bestmove)
            alpha = -9999999

            for move in movelist:

                game.push(move)
                aval = -self.alphabeta(game, depth, -9999999, -alpha)
                game.pop()

                if self.abort:
                    print(f'ID => depth: {depth}, move: {bestmove}, eval: {alpha}')
                    self.move = bestmove
                    return

                if aval > alpha:
                    alpha = aval
                    bestmove = move

            depth = depth+1

            if alpha >= 9999999 or alpha <= -9999999:
                print ('ID => mate score')
                if alpha<-999999:
                    self.move = bestmove
                    self.resigned = True
                    return
                self.move = bestmove
                return
                
        
        if alpha < -500:
            print(f'ID => Resigned, depth: {depth}, move: {bestmove}, eval: {alpha}')
            self.move = bestmove
            self.resigned = True
            return
        print(f'ID => maxdepth reached, depth: {depth}, move: {bestmove}, eval: {alpha}')
        self.move = bestmove
        return
            
    def alphabeta(self, game, depth, alpha, beta):


        hash = chess.polyglot.zobrist_hash(game)

        if hash in self.transposition:
            if depth <= self.transposition.get(hash)[1][0]:
                return self.transposition.get(hash)[0][0]
            else:
                bestmove = self.transposition.get(hash)[2][0]
                movelist = self.ordermoves(game, bestmove)

        elif depth == 0:
            return self.dinamiceval(game, alpha, beta)

        else:
            movelist = self.ordermoves(game, chess.Move.null())
            # detects if the game endded
            if len(movelist) == 0:
                if game.is_checkmate(): return -9999999
                else: return 0
            elif game.can_claim_threefold_repetition():
                return 0
            bestmove = movelist[0]

        for move in movelist:
            game.push(move)
            temp = -self.alphabeta(game, depth-1, -beta, -alpha)
            game.pop()

            if self.abort: return 0

            if temp >= beta:
                self.cutoff += 1
                return beta
            
            if temp > alpha:
                alpha = temp
                bestmove = move
        
        self.transposition.update({hash: [[alpha], [depth], [bestmove], [self.movenumber]]})

        return alpha

    def dinamiceval(self, game, alpha, beta):

        aval = self.eval(game)
        if aval >= beta:
            return beta
        
        if aval > alpha:
            alpha = aval
        
        movelist = self.captureordering(game)

        for move in movelist:

            if game.is_capture(move):
                game.push(move)
                aval = -self.dinamiceval(game, -beta, -alpha)
                game.pop()

                if aval >= beta:
                    return beta
                
                if aval > alpha:
                    alpha = aval
                
        return alpha

    def ordermoves(self, game, bestmove):

        moves = list(game.legal_moves)
        if bestmove != chess.Move.null():
            movesordered = [bestmove]
            moves.pop(moves.index(bestmove))
        else:
            movesordered = []

        i = 0
        for move in moves:
            
            if game.gives_check(move):
                movesordered.append(move)
                moves.pop(i)
            i = i+1

        i = 0
        captures = {}
        for move in moves:
            
            if game.is_capture(move):
                if game.is_en_passant(move):
                    captures.update({move: 0})
                else:
                    captures.update({move: self.capturescore(game, move)})
                moves.pop(i)
            i = i+1

        sorte =  sorted(captures.items(), key = lambda x:x[1], reverse = True)
        for move in sorte:
            movesordered.append(move[0])

        i = 0
        for move in moves:
            if move.promotion:
                movesordered.append(move)
                moves.pop(i)

            i = i + 1

        i = 0
        for move in moves:
            if game.is_castling(move):
                movesordered.append(move)
                moves.pop(i)

            i = i + 1

        for move in moves:
            movesordered.append(move)
        
        return movesordered

    def capturescore (self, game, move):
        return self.piecevalue(game.piece_at(move.to_square)) - self.piecevalue(game.piece_at(move.from_square))

    def piecevalue(self, piece):
        if piece.piece_type == 1: return 1
        elif piece.piece_type == 2: return 3
        elif piece.piece_type == 3: return 3
        elif piece.piece_type == 4: return 5
        elif piece.piece_type == 5: return 9
        else: return 0

    def captureordering (self, game):
        
        moves = game.legal_moves
        movesordered = []
        captures = {}

        for move in moves:
            if game.is_capture(move):
                if game.is_en_passant(move):
                    captures.update({move: 0})
                else:
                    captures.update({move: self.capturescore(game, move)})

        sorte =  sorted(captures.items(), key = lambda x:x[1], reverse = True)
        for move in sorte:
            movesordered.append(move[0])

        return movesordered

    def eval(self, game):
        self.nodes += 1
        
        hash = chess.polyglot.zobrist_hash(game)

        if hash in self.evaltt:
            return self.evaltt.get(hash)[0]

        
        if len(list(game.legal_moves)) == 0:
            if game.is_checkmate(): return -9999999
            else: return 0
        elif game.can_claim_threefold_repetition():
            return 0

        else:

            self.wp = game.pieces(chess.PAWN, chess.WHITE)
            self.bp = game.pieces(chess.PAWN, chess.BLACK)
            self.wn = game.pieces(chess.KNIGHT, chess.WHITE)
            self.bn = game.pieces(chess.KNIGHT, chess.BLACK)
            self.wb = game.pieces(chess.BISHOP, chess.WHITE)
            self.bb = game.pieces(chess.BISHOP, chess.BLACK)
            self.wr = game.pieces(chess.ROOK, chess.WHITE)
            self.br = game.pieces(chess.ROOK, chess.BLACK)
            self.wq = game.pieces(chess.QUEEN, chess.WHITE)
            self.bq = game.pieces(chess.QUEEN, chess.BLACK)
            self.wking = game.king(chess.WHITE)
            self.bking = game.king(chess.BLACK)
            nofpieces = self.pieces()

            if game.turn == chess.WHITE:
                score = self.pawns(game) + self.kingposition(nofpieces, game) + self.bishops(game) + self.knights(game) + self.rooks(game) + self.queens(game)
            else:
                score = - (self.pawns(game) + self.kingposition(nofpieces, game) + self.bishops(game) + self.knights(game) + self.rooks(game) + self.queens(game))

            self.evaltt.update({hash : [score, self.movenumber]})

            return score

    def pieces (self):
        return len(self.wn) + len(self.bn) + len(self.wb) + len(self.bb) + len(self.wr) + len(self.br) + 3*(len(self.wq) + len(self.bq))

    def kingposition (self, nofpieces, game):

        if nofpieces > 10:
            score = 0
            for s in game.attacks(self.wking):
                if game.is_attacked_by(chess.BLACK, s):
                    score -= 20
            for s in game.attacks(self.bking):
                if game.is_attacked_by(chess.WHITE, s):
                    score += 20
            return self.kingmap[self.wking] + self.kingmap[self.bking] + score
        else:
            w = (chess.square_file(self.wking) - 4)**2
            b = (chess.square_file(self.bking) - 4)**2
            return -w + (chess.square_rank(self.wking)*3) + b + (chess.square_rank(self.bking)*3)

    def bishops (self, game):
        
        score = 0
        if len(self.wb) == 2:
            for wb in self.wb:
                score += 2*len(game.attacks(wb)) + 350

        else:
            for wb in self.wb:
                score += 2*len(game.attacks(wb)) + 315
                for wp in self.wp:
                    if wp%2 == wb%2:
                        score = score - 14

        if len(self.bb) == 2:
            for bb in self.bb:
                score = score - 2*len(game.attacks(bb)) - 350
        else:
            for bb in self.bb:
                score = score - 2*len(game.attacks(bb)) - 315
                for bp in self.bp:
                    if bp%2 == bb%2:
                        score = score + 14
        return score

    def pawns (self, game):

        s = 0
        for p in self.wp:
            s += 100
            r = chess.square_rank(p)
            passed = True
            for i in range(8-r):
                if (p+8*(1+i)) < 56:
                    if game.piece_at(p+8*(1+i)) == chess.Piece(1, chess.BLACK): passed = False
                    elif game.piece_at(p+8*(1+i)) == chess.Piece(1, chess.WHITE): s -= 40
            if passed:
                s = s + 40 + 2*(r**2)
            if chess.square_distance(p, self.wking) < 3: s = s + 30

        for p in self.bp:
            s -= 100
            r = chess.square_rank(p)
            passed = True
            for i in range(r):
                if (p-8*(1+i)) > 7:
                    if game.piece_at(p-8*(1+i)) == chess.Piece(1, chess.WHITE): passed = False
                    elif game.piece_at(p-8*(1+i)) == chess.Piece(1, chess.BLACK): s += 40
            if passed:
                s = s - 40 - 2*((8-r)**2)
            if chess.square_distance(p, self.bking) < 3: s = s - 30

        return s

    def rooks (self, game):

        s = 0
        for r in self.wr:
            s += len(game.attacks(r)) + 500

        for r in self.br:
            s -= (len(game.attacks(r)) + 500)
        return s

    def queens (self, game):

        s = 0
        for q in self.wq:
            s += 900 + len(game.attacks(q))/2

        for q in self.bq:
            s = s - 900 - len(game.attacks(q))/2
        return s





        ''''
        while i < len(wp) - 1:
            if chess.square_distance(wp[i], wp[i+1]) == 1:
                score = score + 5
            if chess.square_distance(wp[i], self.wking) <= 2:
                score = score + 10
            score = score + chess.square_file(wp[i])
            i = i + 1
        score = score + chess.square_file(wp[len(wp)-1])
        i = 0
        while i < len(bp) - 1:
            if chess.square_distance(bp[i], bp[i+1]) == 1:
                score = score - 5
            if chess.square_distance(bp[i], self.bking) <= 2:
                score = score - 10
            score = score - chess.square_file(bp[i])
            i = i + 1
        score = score - chess.square_file(bp[len(bp)-1])
        return score'''

    def knights (self, game):

        score = 0
        for i in self.wn:
            score = score + 300 + self.knightmap[i] - 2*(chess.square_distance(i, self.wking) - len(game.attacks(i)))
        
        for j in self.bn:
            score = score - 300 - self.knightmap[j] + 2*(chess.square_distance(j, self.bking) - len(game.attacks(j)))

        return score
    
    def timemanegement (self, game, maxtime, *args):
        self.shouldabort = True
        if maxtime.time is None:
            if self.movenumber < 15:
                if game.turn == chess.WHITE:
                    maxtime = maxtime.white_clock/20
                else:
                    maxtime = maxtime.black_clock/20
            else:
                if game.turn == chess.WHITE:
                    maxtime = maxtime.white_clock/13
                else:
                    maxtime = maxtime.black_clock/13
        else:
            maxtime = maxtime.time
        
        print('Tempo:', maxtime)
        time.sleep(maxtime)
        if self.shouldabort:
            self.abort = True

    def ponder (self, newmove, game, *args):

        self.cleanse = True
        game.push(newmove)
        maxdepth = 5
        bestmove = chess.Move.null()
        depth = 0
        
        if self.movenumber % 2 == 0:

            for hash in self.transposition:
                temp = self.transposition.get(hash)
                if (self.movenumber - temp[3][0]) > 2:
                    self.temptt.update({hash: self.transposition.get(hash)})

            for hash in self.evaltt:
                temp = self.evaltt.get(hash)
                if (self.movenumber - temp[1]) > 3:
                    self.tempeval.update({hash: temp})

            self.transposition = self.temptt
            self.evaltt = self.tempeval
            self.temptt = {}
            self.tempeval = {}

        self.cleanse = False

        while (depth <= maxdepth):

            movelist = self.ordermoves (game, bestmove)
            alpha = -9999999

            for move in movelist:

                game.push(move)
                aval = -self.alphabetaponder(game, depth, -9999999, -alpha)
                game.pop()

                if self.abort_ponder:
                    game.pop()
                    print(f'ponder => depth: {depth}, move: {bestmove}, eval: {alpha}') 
                    return

                if aval > alpha:
                    alpha = aval
                    bestmove = move

            depth = depth+1

            if alpha >= 9999999 or alpha <= -9999999:
                game.pop()
                print ('ponder: mate score')
                return

        print ('ponder reached maxdepth')    
        return
         
    def alphabetaponder (self, game, depth, alpha, beta):

        hash = chess.polyglot.zobrist_hash(game)

        if hash in self.transposition:
            if depth <= self.transposition.get(hash)[1][0]:
                return self.transposition.get(hash)[0][0]
            else:
                bestmove = self.transposition.get(hash)[2][0]
                movelist = self.ordermoves(game, bestmove)

        elif depth == 0:
            return self.dinamiceval(game, alpha, beta)

        else:
            movelist = self.ordermoves(game, chess.Move.null())
            # detects if the game endded
            if len(movelist) == 0:
                if game.is_checkmate(): return -9999999
                else: return 0
            elif game.can_claim_threefold_repetition():
                return 0
            bestmove = movelist[0]

        for move in movelist:
            game.push(move)
            temp = -self.alphabetaponder(game, depth-1, -beta, -alpha)
            game.pop()

            if self.abort_ponder: return 0

            if temp >= beta:
                self.cutoff += 1
                return beta
            
            if temp > alpha:
                alpha = temp
                bestmove = move
        
        self.transposition.update({hash: [[alpha], [depth], [bestmove], [self.movenumber]]})

        return alpha

