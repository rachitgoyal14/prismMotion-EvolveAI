"""
Validate generated Manim code before attempting to render.
Catches common issues: missing imports, syntax errors, undefined variables.
"""
import ast
import re
from typing import Tuple, Optional

import logging
logger = logging.getLogger(__name__)


class ManimCodeValidator:
    """Validates Manim-generated Python code."""
    
    REQUIRED_IMPORTS = ["from manim import *"]
    FORBIDDEN_PATTERNS = [
        r"\bFRAME_WIDTH\b",  # Should use config.frame_width
        r"\bFRAME_HEIGHT\b",  # Should use config.frame_height
        r"config\.background_color\s*=",  # Should use self.camera.background_color
        r"SVGMobject\s*\([^)]*path_string\s*=",  # SVGMobject doesn't accept path_string
        r"\.set_points_as_corners\s*\(\s*\[",  # Often misused
    ]
    
    def validate(self, code: str, scene_id: int) -> Tuple[bool, Optional[str]]:
        """
        Validate Manim code.
        
        Args:
            code: Python code string
            scene_id: Expected scene ID
        
        Returns:
            (is_valid, error_message)
            - (True, None) if valid
            - (False, "error description") if invalid
        """
        # Check 1: Has required imports
        if not self._has_required_imports(code):
            return False, "Missing 'from manim import *' at the top"
        
        # Check 2: Syntax is valid Python
        syntax_error = self._check_syntax(code)
        if syntax_error:
            return False, f"Syntax error: {syntax_error}"
        
        # Check 3: Has correct Scene class
        class_error = self._check_scene_class(code, scene_id)
        if class_error:
            return False, class_error
        
        # Check 4: No forbidden patterns
        forbidden_error = self._check_forbidden_patterns(code)
        if forbidden_error:
            return False, forbidden_error
        
        # Check 5: Has construct method
        if not self._has_construct_method(code):
            return False, "Missing construct() method in Scene class"
        
        return True, None
    
    def _has_required_imports(self, code: str) -> bool:
        """Check if code has required imports."""
        for required in self.REQUIRED_IMPORTS:
            if required not in code:
                return False
        return True
    
    def _check_syntax(self, code: str) -> Optional[str]:
        """Check if code is syntactically valid Python."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
    
    def _check_scene_class(self, code: str, scene_id: int) -> Optional[str]:
        """Check if Scene class exists with correct name."""
        expected_class = f"Scene{scene_id}"
        
        # Parse AST and find class definitions
        try:
            tree = ast.parse(code)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            if expected_class not in classes:
                return f"Missing class '{expected_class}'. Found classes: {classes}"
            
            # Check if it inherits from Scene
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == expected_class:
                    if not node.bases:
                        return f"Class '{expected_class}' must inherit from Scene"
                    # Check if "Scene" is in base names
                    base_names = [
                        base.id if isinstance(base, ast.Name) else str(base)
                        for base in node.bases
                    ]
                    if "Scene" not in base_names:
                        return f"Class '{expected_class}' must inherit from Scene, found: {base_names}"
            
            return None
        except Exception as e:
            return f"Error checking class structure: {e}"
    
    def _check_forbidden_patterns(self, code: str) -> Optional[str]:
        """Check for known problematic patterns."""
        for pattern in self.FORBIDDEN_PATTERNS:
            match = re.search(pattern, code)
            if match:
                matched_text = match.group()
                
                if "FRAME_WIDTH" in matched_text or "FRAME_HEIGHT" in matched_text:
                    return (
                        f"Found usage of {matched_text} which is not defined. "
                        f"Use 'config.frame_width' or 'config.frame_height' instead, "
                        f"and make sure to import config: 'from manim import config'"
                    )
                elif "config.background_color" in matched_text:
                    return (
                        f"Found 'config.background_color = ...' which doesn't work. "
                        f"Use 'self.camera.background_color = ...' instead"
                    )
                elif "SVGMobject" in matched_text and "path_string" in matched_text:
                    return (
                        f"SVGMobject doesn't accept 'path_string' parameter. "
                        f"Use VMobject with .set_points_as_corners() instead, or use basic shapes like Circle, Rectangle, Polygon. "
                        f"Example: checkmark = VMobject(); checkmark.set_points_as_corners([start, middle, end])"
                    )
        
        return None
    
    def _has_construct_method(self, code: str) -> bool:
        """Check if Scene class has construct method."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    method_names = [
                        n.name for n in node.body 
                        if isinstance(n, ast.FunctionDef)
                    ]
                    if "construct" in method_names:
                        return True
            return False
        except:
            return False


def validate_manim_code(code: str, scene_id: int) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to validate Manim code.
    
    Args:
        code: Python code string
        scene_id: Expected scene ID
    
    Returns:
        (is_valid, error_message)
    """
    validator = ManimCodeValidator()
    is_valid, error = validator.validate(code, scene_id)
    
    if is_valid:
        logger.info(f"✓ Scene {scene_id} code validation passed")
    else:
        logger.error(f"✗ Scene {scene_id} code validation failed: {error}")
    
    return is_valid, error