# Perform a Breadth-First Search (BFS) traversal on a graph-like structure starting from the given node.
from collections import deque
from .error import OpgeeException


def is_cyclic_until(successor, visited, rec_stack, successors):
    """
        Helper function to determine if there is a cycle in the given successors starting from the current successor.

        Args:
            successor (Node): The current node being examined for cycles.
            visited (dict): A dictionary to keep track of visited nodes.
            rec_stack (dict): A dictionary to keep track of nodes in the recursion stack.
            successors (list): A list of successors to check for cycles.

        Returns:
            bool: True if a cycle is found, False otherwise.
    """

    visited[successor] = True
    rec_stack[successor] = True

    for successor_successor in successor.successors():
        if successor_successor not in successors:
            continue
        if successor_successor not in visited:
            if is_cyclic_until(successor_successor, visited, rec_stack, successors):
                return True
        elif rec_stack[successor_successor]:
            return True

    rec_stack[successor] = False
    return False


def is_cyclic(successors):
    """
        Determines if there is a cycle in the given successors list.

        Args:
            successors (list): A list of successors to check for cycles.

        Returns:
            bool: True if a cycle is found, False otherwise.
    """
    visited = {}
    rec_stack = {}
    for successor in successors:
        if successor not in visited:
            if is_cyclic_until(successor, visited, rec_stack, successors):
                return True
    return False


def find_distance_bfs(start_node, successors_dist_dict, visited):
    """
        Helper function to perform a Breadth-First Search (BFS) traversal to calculate the maximum distance for each node.

        Args:
            start_node (Node): The starting node for the BFS traversal.
            successors_dist_dict (dict): A dictionary that stores the maximum distance for each node.
            visited (dict): A dictionary to keep track of visited nodes during the traversal.
    """
    queue = deque([start_node])

    visited[start_node] = True
    while queue:
        current_node = queue.popleft()
        current_distance = successors_dist_dict[current_node]

        for child_node in current_node.successors():
            if child_node not in successors_dist_dict:
                successors_dist_dict[child_node] = 0

            if child_node not in visited:
                child_distance = successors_dist_dict[child_node]
                new_child_distance = max(child_distance, current_distance + 1)
                successors_dist_dict[child_node] = new_child_distance
                queue.append(child_node)
                visited[child_node] = True


def get_successor_pairs(successors):
    """
       Calculate the maximum distance from the starting node to each node in the successors list.

       Args:
           successors (list): A list of successors.

       Returns:
           list: A list of tuples, where each tuple contains a successor node and its maximum distance from the starting node.
   """
    successors_dist_dict = {}
    for successor in successors:
        successors_dist_dict[successor] = 0

    for successor in successors:
        find_distance_bfs(successor, successors_dist_dict, {})

    return list(successors_dist_dict.items())


def bfs(start_node, unvisited, ordered_cycle):
    """
        Perform a Breadth-First Search (BFS) traversal on a graph-like structure starting from the given node.

        Args:
            start_node: The starting node for the BFS traversal.

        Returns:
            ordered_cycle (list): A list containing the nodes visited in the order they were visited during the BFS traversal.
            :param start_node:
            :param ordered_cycle:
            :param unvisited:
    """
    deck = deque([start_node])

    while deck:
        current_node = deck.popleft()

        if current_node in unvisited:
            unvisited.remove(current_node)
            ordered_cycle.append(current_node)

            successors = [successor for successor in current_node.successors() if successor in unvisited]

            if is_cyclic(successors):
                raise OpgeeException(f"Cycle detected in process {current_node} with successors {successors}")
            else:
                successors_pairs = get_successor_pairs(successors)
            successors_pairs.sort(key=lambda x: x[1])
            for successor in successors_pairs:
                deck.append(successor[0])
