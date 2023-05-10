import math
import pickle
from constants import *
from run import GameController 
import sys
import time

class State:
    def __init__(self, p1):
        self.state = []
        self.p1 = p1
        self.isEnd = False
        self.finalScore = 0
        self.closeDistance = 80
        self.closestPellet = None
        self.ghostDistance = 0
        self.lastghostDistance = 0
        self.closeDistance = sys.maxsize
        self.time = int(time.time())
    
    def availableDirections(self, pacman):
        return pacman.validDirections()

    # Returns the direction of the closest ghost relative to pacman
    # if the ghost is within a certain range. Else, returns None.
    def getGhostDirections(self, ghosts, pacman_target):
        directions = []
        for ghost in ghosts:
            
            distance = math.sqrt((pacman_target.y - ghost.position.x)**2 + (pacman_target.y - ghost.position.y)**2)           
            
            vec = (ghost.position.x - pacman_target.x, ghost.position.y - pacman_target.y)
            if abs(vec[1]) >= abs(vec[0]): 
                if vec[1] >= 0:
                    directions.append((DOWN, int(distance), ghost.mode.current))
                else:
                   directions.append((UP, int(distance), ghost.mode.current))
            else: 
                if vec[0] >= 0:
                    directions.append((RIGHT, int(distance), ghost.mode.current))
                else:
                    directions.append((LEFT, int(distance), ghost.mode.current)) 

        sorted_distance = []

        while len(directions):
            index_to_remove = -1
            smallest_distance = sys.maxsize
            current_direction = None
            current_mode = None
            current_index = -1
            for (direction, distance, mode) in directions:
                current_index += 1
                if(distance < smallest_distance):
                    smallest_distance = distance
                    index_to_remove = current_index
                    current_direction = direction
                    current_mode = mode
            sorted_distance.append((current_direction, int(smallest_distance), current_mode))
            del directions[index_to_remove]


        return sorted_distance
    
    def getClosestPellet(self, pellets, pacman_target):
        closest_pellet = None
        closest_distance = sys.maxsize
        for pellet in pellets.pelletList:
            pellet.color = WHITE
            distance = math.sqrt((pacman_target.x - pellet.position.x)**2 + (pacman_target.y - pellet.position.y)**2)
            if closest_pellet is None or distance < closest_distance:
                closest_pellet = pellet
                closest_distance = distance

        if closest_pellet:
            self.closestPellet = closest_pellet
            self.closeDistance = closest_distance
            closest_pellet.color = RED
            
            vec = (closest_pellet.position.x - pacman_target.x, closest_pellet.position.y - pacman_target.y)
            if abs(vec[1]) >= abs(vec[0]): 
                if vec[1] >= 0:
                    return DOWN, int(closest_distance)
                else:
                    return UP, int(closest_distance)
            else: 
                if vec[0] >= 0:
                    return RIGHT, int(closest_distance)
                else:
                    return LEFT, int(closest_distance)    
        else:
            return None, -1

    # Updates the state with the current game world's information.
    def updateState(self, ghosts, pacman_target, pacman_pos, pellets):
        curGhostDirections = self.getGhostDirections(ghosts, pacman_pos)
        closetPelletDirection = self.getClosestPellet(pellets, pacman_pos)
        
        self.state = [int(pacman_target[0]), int(pacman_target[1]),
                      curGhostDirections[0][0],
                      curGhostDirections[1][0],
                      curGhostDirections[2][0],
                      curGhostDirections[3][0],
                      closetPelletDirection[0], closetPelletDirection[1]]
        
        #curGhostDirection = self.getGhostDirections(ghosts, pacman_pos)
        #self.state = [closestPelletDir]
    
    

    # Apply the chosen action (direction) to the game.
    def applyAction(self, game, direction):
        game.pacman.learntDirection = direction
        game.update()
    
    # Checks if game is over i.e. level completed or all lives lost.
    def gameEnded(self, game):
        if game.lives <= 0 :
            self.isEnd = True
            self.finalScore = game.score
            with open("scores.txt", "a") as myfile:
                myfile.write(str(self.finalScore) + "\n")
            self.level = 0
            return 0
        if len(game.pellets.pelletList) <= 0:
            self.isEnd = True
            self.finalScore = game.score
            self.level += 1
        if game.level > self.level:
            return 1
        if USETIMER and (self.time + 20 < int(time.time())):
            self.isEnd = True
            self.finalScore = game.score
            return 1
        else:
            return None
    
    # Checks if game is paused i.e. after one life is lost or at the
    # beginning of new game. If it is, resumes it.
    def gamePaused(self, game):
        if game.pause.paused:
            if game.pacman.alive:
                game.pause.setPause(playerPaused=True)
                if not game.pause.paused:
                    game.textgroup.hideText()
                    game.showEntities()

    # Main method for training.
    def play(self, file, iterations=100):
        for i in range(iterations):
            if i % 1 == 0:
                print("Iterations {}".format(i))
            if i % 50 == 0 and SAVEPOLICY:
                p1.savePolicy(file)
            game = GameController()
            game.startGame()
            game.update()
            pacman_target = game.nodes.getPixelsFromNode(game.pacman.target)
            pacman_pos = game.pacman.position
            self.updateState(game.ghosts, pacman_target, pacman_pos, game.pellets)
            self.level = game.level
            lastAliveStatus = True
            
            self.time = int(time.time())
            while not self.isEnd:
                currentAliveStatus = game.pacman.alive
                died = False
                if not currentAliveStatus and lastAliveStatus:
                    died = True
                lastAliveStatus = currentAliveStatus

                possible_directions = self.availableDirections(game.pacman)
                p1_action = self.p1.getAction(self.state, possible_directions, game.score, died)
                # take action and update board state
                self.applyAction(game, p1_action)
                pacman_target = game.nodes.getPixelsFromNode(game.pacman.target)
                pacman_pos = game.pacman.position
                self.updateState(game.ghosts, pacman_target, pacman_pos, game.pellets)

                # check board status if it is end
                self.gamePaused(game)
                result = self.gameEnded(game)
                if result is not None:
                    self.p1.final(self.state, game.score)
                    game.restartGame(self.level)
                    self.closestPellet = None
                    self.closeDistance = sys.maxsize
                    del game
                    self.isEnd = False
                    break

                else:
                    # next frame iteration
                    continue



if __name__ == "__main__":
    #### PARAMETERS:
    # ALPHA -> Learning Rate
    # controls how much influence the current feedback value has over the stored Q-value.

    # GAMMA -> Discount Rate
    # how much an action’s Q-value depends on the Q-value at the state (or states) it leads to.

    # RHO -> Randomness of Exploration
    # how often the algorithm will take a random action, rather than the best action it knows so far.

    # NU: The Length of Walk
    # number of iterations that will be carried out in a sequence of connected actions.
    
    exploration_rho = 0.3
    lr_alpha = 0.2
    discount_rate_gamma=0.9
    walk_len_nu = 0.2
    
    # training
    from player import *
    fileName = "trained_controller_final"
    

    """
    p1 = Player("p1", exploration_rho, lr_alpha, discount_rate_gamma, walk_len_nu)
    st = State(p1)

 
    # # # TRAINING
    ("Training...")
    st.play(fileName, 10000)
    p1.savePolicy(fileName)
    
    """
    # DEMO
    demo_p1 = Player("demo", exploration_rho=0, lr_alpha=0)
    demo_p1.loadPolicy(fileName)
    stDemo = State(demo_p1)
    stDemo.play(fileName)
    