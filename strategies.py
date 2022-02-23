"""
Some example strategies for people who want to create a custom, homemade bot.
And some handy classes to extend
"""

import chess
from chess.engine import PlayResult
from engine_wrapper import EngineWrapper
#from alphabeta import alphabeta, moveordering
import time
#lip_JYnnhvNoXJwO6ejjx8ep

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

        self.knightmap = [
            -10, -10, -10, -10, -10, -10, -10, -10, 
            -10, -10,  -5,   0,   0,  -5,  -5, -10, 
            -10,  -5,   5,   0,   0,   5,  -5, -10,
            -5,    0,   5,  10,  10,   5,   0,  -5,
            -5,    0,   5,  10,  10,   5,   0,  -5,
            -10,  -5,   0,   0,   0,   5,  -5, -10,
            -10, -10,  -5,   0,   0,  -5, -10, -10,
            -10, -10, -10, -10, -10, -10, -10, -10, 
        ]

    '''
   def search(self, game, *args):
        self.transposition = {}
        movelist = moveordering(game, chess.Move.null())
        alpha = -9999999
        bestmove = movelist[0]

        for move in movelist:
            game.push(move)
            aval = -alphabeta(game, 2, -9999999, -alpha)
            game.pop()
            print('n:', move, ',', aval)

            if aval > alpha:
                alpha = aval
                bestmove = move
            
        return PlayResult(bestmove, None)
        '''

    def search (self, game, maxtime, *args):
        
        if maxtime.time is None:
            maxtime = min(maxtime.white_clock, maxtime.black_clock)/10
        else:
            maxtime = maxtime.time

        inicio = time.time()
        maxdepth = 9
        bestmove = chess.Move.null()
        depth = 0
        if len(list(game.legal_moves)) == 1:
            return PlayResult(list(game.legal_moves)[0], None)

        while (depth <= maxdepth):
            print('Depth:', depth)
            movelist = self.moveordering (game, bestmove)
            alpha = -9999999
            bestmove = movelist[0]

            for move in movelist:

                if (time.time()-inicio) >= maxtime:
                        print(time.time()-inicio)
                        return PlayResult(bestmove, None)

                game.push(move)
                aval = -self.alphabeta(game, depth, -9999999, -alpha)
                game.pop()
                print(move)

                if aval > alpha:
                    alpha = aval
                    bestmove = move

            depth = depth+1
            if alpha >= 9999999 or alpha <= -9999999:
                PlayResult(bestmove, None)

        return PlayResult(bestmove, None)
            
    def alphabeta(self, game, depth, alpha, beta):

        hash = chess.polyglot.zobrist_hash(game)

        if hash in self.transposition:
            if depth <= self.transposition.get(hash)[1][0]:
                return self.transposition.get(hash)[0][0]
            else:
                bestmove = self.transposition.get(hash)[2][0]
                movelist = self.moveordering(game, bestmove)

        elif depth == 0:
            return self.dinamiceval(game, alpha, beta)

        else:
            movelist = self.moveordering(game, chess.Move.null())

        # detects if the game endded
        if len(movelist) == 0:
            if game.is_checkmate(): return -9999999
            else: return 0
        
        bestmove = movelist[0]

        for move in movelist:
            game.push(move)
            temp = -self.alphabeta(game, depth-1, -beta, -alpha)
            game.pop()

            if temp >= beta:
                self.transposition.update({hash: [[beta], [depth], [move]]})
                return beta
            
            if temp > alpha:
                alpha = temp
                bestmove = move
        
        self.transposition.update({hash: [[alpha], [depth], [bestmove]]})

        return alpha

    def dinamiceval(self, game, alpha, beta):

        aval = self.eval(game)
        if aval >= beta:
            return beta
        
        if aval > alpha:
            alpha = aval
        
        movelist = list(game.legal_moves)

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

    def moveordering(self, game, bestmove):

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
        for move in moves:
            
            if game.is_capture(move):
                movesordered.append(move)
                moves.pop(i)
            i = i+1

        i = 0
        for move in moves:
            
            if move.promotion:
                movesordered.append(move)
                moves.pop(i)
            i = i+1

        i = 0
        for move in moves:
            
            if game.is_castling(move):
                movesordered.append(move)
                moves.pop(i)
            i = i+1

        for move in moves:
            
                movesordered.append(move)
        
        return movesordered

    def eval(self, game):
        
        hash = chess.polyglot.zobrist_hash(game)

        if hash in self.evaltt:
            if len(list(game.legal_moves)) == 0:
                if game.is_checkmate(): return -9999999
                else: return 0
            else: return self.evaltt.get(hash)

        if game.turn == chess.WHITE:
            me = chess.WHITE
            oponent = chess.BLACK
        else:
            oponent = chess.WHITE
            me = chess.BLACK

        
        if len(list(game.legal_moves)) == 0:
            if game.is_checkmate(): return -9999999
            else: return 0

        else:

            score = self.material(game, me, False) - self.material(game, oponent, False)

            pieces = self.material(game, me, True) + self.material(game, oponent, True)

            score = score + 2*(self.kingpositioning(game, me, pieces) - self.kingpositioning(game, oponent, pieces))

            score = score + self.bishops(game, me) - self.bishops(game, oponent)

            score = score + self.knights(game, me) - self.knights(game, oponent)

            score = score + self.pawns (game, me) - self.pawns (game, oponent)

            score = score + self.mobility(game)

            self.evaltt.update({hash : score})

            return score

    def material(self, game, color, count):
        p = len(game.pieces(chess.PAWN, color))
        n = len(game.pieces(chess.KNIGHT, color))
        b = len(game.pieces(chess.BISHOP, color))
        r = len(game.pieces(chess.ROOK, color))
        q = len(game.pieces(chess.QUEEN, color))
        if count:
            return n + b + r + 3*q
        else:
            return p*100 + n*300 + b*315 + r*500 + q*900

    def mobility(self, game):
        game.push(chess.Move.null())
        oponentmobility = len(list(game.pseudo_legal_moves))
        game.pop()
        return (len(list(game.pseudo_legal_moves)) - oponentmobility)

    def kingpositioning (self, game, color, pieces):

        if pieces > 10:
            r = (chess.square_file(game.king(color)) - 4)**2
            if color == chess.WHITE:
                return r - (chess.square_rank(game.king(color))*2)
            else:
                return r + (chess.square_rank(game.king(color))*2)
        else:
            r = -((chess.square_file(game.king(color)) - 4)**2)
            if color == chess.WHITE:
                return r + (chess.square_rank(game.king(color))*2)
            else:
                return r - (chess.square_rank(game.king(color))*2)

    def bishops (self, game, color):
        b = list(game.pieces(chess.BISHOP, color))
        score = 0
        if len(b) == 2:
            return 80
        elif len(b) == 1:
            for p in game.pieces(chess.PAWN, color):
                if p%2 == b[0]%2:
                    score = score - 2
        return score

    def pawns (self, game, color):
        p = list(game.pieces(chess.PAWN, color))
        score = 0
        i = 0
        while i < len(p) - 1:
            if chess.square_distance(p[i], p[i+1]) == 1:
                score = score + 5
            if chess.square_distance(p[i], game.king(color)) <= 2:
                score = score + 10
            score = score + chess.square_file(p[i])
            i = i + 1
        return score

    def knights (self, game, color):
        n = list(game.pieces(chess.KNIGHT, color))
        
        if len(n) == 0:
            return 0
        else:
            for i in n:
                score = self.knightmap[i]
                score = score - 2*chess.square_distance(i, game.king(color))
            return score
