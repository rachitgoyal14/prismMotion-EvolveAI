"""
Validate generated Manim code before attempting to render.
Catches common issues: missing imports, syntax errors, undefined variables, and ImageMobject pitfalls.
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
        r"ImageMobject\([^)]+\)\.scale_to_fit_width",  # Dangerous: causes crashes
        r"FadeIn\s*\(\s*ImageMobject",  # Dangerous: direct FadeIn on ImageMobject
        r"VGroup\s*\([^)]*VGroup\s*\(\s*[^)]*ImageMobject",  # Nested VGroups with ImageMobject
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
        
        # Check 4: No forbidden patterns (including image issues)
        forbidden_error = self._check_forbidden_patterns(code)
        if forbidden_error:
            return False, forbidden_error
        
        # Check 5: Has construct method
        if not self._has_construct_method(code):
            return False, "Missing construct() method in Scene class"
        
        # Check 6: ImageMobject usage is safe
        image_error = self._check_image_mobject_safety(code)
        if image_error:
            return False, image_error
        
        return True, None
    
    def _has_required_imports(self, code: str) -> bool:
        """Check if code has required imports."""
        for required in self.REQUIRED_IMPORTS:
            if required not in code:
                return False
        
        # If using config.frame_width/height, must import config
        if "config.frame" in code and "from manim import config" not in code:
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
                        f"Use VMobject with .set_points_as_corners() instead, or use basic shapes."
                    )
                elif "scale_to_fit_width" in matched_text and "ImageMobject" in code:
                    return (
                        f"Found 'ImageMobject(...).scale_to_fit_width()' which causes crashes with large images. "
                        f"Use 'image.height = config.frame_height * 0.4' instead. "
                        f"Example: bg_image.height = config.frame_height * 0.4"
                    )
                elif "FadeIn" in matched_text and "ImageMobject" in matched_text:
                    return (
                        f"Found 'FadeIn(ImageMobject(...))' which can hang during rendering. "
                        f"Use 'self.add(image)' first, then 'self.play(image.animate.set_opacity(0.7))'. "
                        f"Example: self.add(bg_image); self.play(bg_image.animate.set_opacity(0.7), run_time=1)"
                    )
                elif "VGroup" in matched_text and "ImageMobject" in code:
                    return (
                        f"Found nested VGroups containing ImageMobject, which can cause issues. "
                        f"Fade out ImageMobject separately: self.play(FadeOut(text), FadeOut(image))"
                    )
        
        return None
    
    def _check_image_mobject_safety(self, code: str) -> Optional[str]:
        """Check ImageMobject usage for common crash patterns."""
        if "ImageMobject" not in code:
            return None  # No images, no problem
        
        # Check 1: Must use try/except when loading images
        if "ImageMobject(" in code and "try:" not in code:
            logger.warning("ImageMobject used without try/except - recommended for robustness")
            # Not a hard error, just a warning
        
        # Check 2: Should use .height, not .scale_to_fit_width()
        if "scale_to_fit_width" in code and "ImageMobject" in code:
            return (
                "ImageMobject with scale_to_fit_width() detected - this causes crashes. "
                "Use 'image.height = config.frame_height * 0.4' instead"
            )
        
        # Check 3: Should not use direct FadeIn on ImageMobject
        if re.search(r"FadeIn\s*\(\s*\w+\s*\)", code) and "ImageMobject" in code:
            # Check if the FadeIn target might be an image
            if re.search(r"(bg_image|image|photo|picture)\s*=\s*ImageMobject", code):
                return (
                    "Direct FadeIn on ImageMobject detected - this can hang. "
                    "Use: self.add(image); self.play(image.animate.set_opacity(0.7))"
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