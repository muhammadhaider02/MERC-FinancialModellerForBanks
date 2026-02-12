"""
Dependency Graph (DAG) resolution for component execution order.
Ensures components are executed in the correct order based on dependencies.
"""
from typing import Dict, List, Set, Callable
from collections import defaultdict, deque


class DAGNode:
    """Node in the dependency graph."""
    
    def __init__(self, name: str, execute_fn: Callable):
        self.name = name
        self.execute_fn = execute_fn
        self.dependencies: Set[str] = set()
    
    def add_dependency(self, dependency_name: str):
        """Add a dependency to this node."""
        self.dependencies.add(dependency_name)
    
    def execute(self, state):
        """Execute this node's function."""
        return self.execute_fn(state)


class DependencyGraph:
    """Manages component dependencies and execution order."""
    
    def __init__(self):
        self.nodes: Dict[str, DAGNode] = {}
    
    def add_node(self, name: str, execute_fn: Callable, dependencies: List[str] = None):
        """
        Add a node to the graph.
        
        Args:
            name: Unique identifier for the node
            execute_fn: Function to execute for this component
            dependencies: List of node names this node depends on
        """
        if name in self.nodes:
            raise ValueError(f"Node '{name}' already exists")
        
        node = DAGNode(name, execute_fn)
        if dependencies:
            for dep in dependencies:
                node.add_dependency(dep)
        
        self.nodes[name] = node
    
    def remove_node(self, name: str):
        """Remove a node from the graph."""
        if name not in self.nodes:
            raise ValueError(f"Node '{name}' does not exist")
        
        # Check if any other nodes depend on this one
        for node_name, node in self.nodes.items():
            if name in node.dependencies:
                raise ValueError(f"Cannot remove '{name}': '{node_name}' depends on it")
        
        del self.nodes[name]
    
    def topological_sort(self) -> List[str]:
        """
        Perform topological sort to determine execution order.
        
        Returns:
            List of node names in execution order
            
        Raises:
            ValueError: If a cycle is detected
        """
        # Calculate in-degree for each node
        in_degree = defaultdict(int)
        for node_name in self.nodes:
            in_degree[node_name] = 0
        
        for node in self.nodes.values():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Dependency '{dep}' not found in graph")
                in_degree[node.name] += 1
        
        # Queue of nodes with no dependencies
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Reduce in-degree for dependent nodes
            for node_name, node in self.nodes.items():
                if current in node.dependencies:
                    in_degree[node_name] -= 1
                    if in_degree[node_name] == 0:
                        queue.append(node_name)
        
        # Check for cycles
        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in dependency graph")
        
        return result
    
    def execute_all(self, state):
        """
        Execute all nodes in dependency order.
        
        Args:
            state: Current simulation state
            
        Returns:
            Updated state after all executions
        """
        execution_order = self.topological_sort()
        
        for node_name in execution_order:
            node = self.nodes[node_name]
            state = node.execute(state)
        
        return state
    
    def validate(self) -> bool:
        """
        Validate the graph for cycles and missing dependencies.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        try:
            self.topological_sort()
            return True
        except ValueError as e:
            raise ValueError(f"Graph validation failed: {e}")
