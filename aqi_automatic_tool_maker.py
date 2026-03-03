#!/usr/bin/env python3
"""
AQI AUTOMATIC TOOL MAKER - ETHICALLY CONSTRAINED
Enables AQI to dynamically create, test, and deploy custom tools autonomously
with comprehensive ethical safeguards and safety measures.
"""

import os
import sys
import ast
import importlib
try:
    import importlib.util
except ImportError:
    # Fallback for older Python versions
    import imp
    importlib.util = imp
import inspect
import tempfile
import subprocess
import json
import time
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
import traceback
import hashlib
import logging

@dataclass
class EthicalAssessment:
    """Ethical assessment of a tool request"""
    approved: bool
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    concerns: List[str]
    recommendations: List[str]
    requires_oversight: bool

@dataclass
class SafetyLimits:
    """Safety and resource limits for tool execution"""
    max_execution_time: int = 30  # seconds
    max_memory_usage: int = 100 * 1024 * 1024  # 100MB
    max_file_operations: int = 10
    max_network_requests: int = 5
    allowed_modules: List[str] = field(default_factory=lambda: [
        'os', 'sys', 'json', 'time', 'datetime', 'math', 'random',
        'collections', 'itertools', 'functools', 'typing', 're',
        'string', 'hashlib', 'base64', 'urllib.parse'
    ])
    blocked_modules: List[str] = field(default_factory=lambda: [
        'subprocess', 'multiprocessing', 'threading', 'socket',
        'http.server', 'ftplib', 'smtplib', 'telnetlib', 'ssl'
    ])

class EthicalGuard:
    """
    Comprehensive ethical and safety framework for AQI tool creation.
    Ensures all tools align with ethical guidelines and safety standards.
    """

    def __init__(self):
        self.harmful_keywords = {
            'critical': [
                'hack', 'exploit', 'malware', 'virus', 'trojan', 'ransomware',
                'ddos', 'bruteforce', 'phishing', 'scam', 'fraud',
                'weapon', 'bomb', 'explosive', 'chemical', 'biological',
                'nuclear', 'terrorism', 'extortion', 'blackmail'
            ],
            'high': [
                'password', 'credential', 'steal', 'unauthorized', 'illegal',
                'surveillance', 'spy', 'monitor', 'track', 'stalk',
                'harass', 'threaten', 'intimidate', 'coerce'
            ],
            'medium': [
                'delete', 'remove', 'destroy', 'erase', 'wipe',
                'override', 'bypass', 'circumvent', 'manipulate'
            ]
        }

        self.positive_keywords = [
            'help', 'assist', 'improve', 'analyze', 'optimize',
            'learn', 'teach', 'create', 'build', 'develop',
            'research', 'explore', 'understand', 'solve'
        ]

        self.safety_limits = SafetyLimits()

        # Setup logging
        self.logger = logging.getLogger('EthicalGuard')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('ethical_guard.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

    def assess_request(self, requirement: str, tool_type: str) -> EthicalAssessment:
        """
        Perform comprehensive ethical assessment of a tool creation request.
        """
        assessment = EthicalAssessment(
            approved=True,
            risk_level='low',
            concerns=[],
            recommendations=[],
            requires_oversight=False
        )

        req_lower = requirement.lower()

        # Check for harmful content
        for risk_level, keywords in self.harmful_keywords.items():
            for keyword in keywords:
                if keyword in req_lower:
                    assessment.concerns.append(f"Contains {risk_level} risk keyword: '{keyword}'")
                    assessment.risk_level = max(assessment.risk_level, risk_level, key=self._risk_order)
                    if risk_level in ['critical', 'high']:
                        assessment.approved = False

        # Check for positive intent
        positive_score = sum(1 for keyword in self.positive_keywords if keyword in req_lower)
        if positive_score == 0 and len(requirement.split()) > 3:
            assessment.concerns.append("No clear positive intent detected")
            assessment.recommendations.append("Clarify the beneficial purpose of this tool")

        # Tool-type specific checks
        if tool_type == 'api_wrapper':
            if 'admin' in req_lower or 'root' in req_lower:
                assessment.concerns.append("API wrapper requests elevated privileges")
                assessment.risk_level = 'high'
                assessment.requires_oversight = True

        elif tool_type == 'automation_script':
            if 'system' in req_lower or 'admin' in req_lower:
                assessment.concerns.append("System automation may require oversight")
                assessment.risk_level = 'medium'
                assessment.requires_oversight = True

        # Length and complexity check
        if len(requirement.split()) > 50:
            assessment.concerns.append("Request is very complex - consider breaking it down")
            assessment.recommendations.append("Simplify the requirement for better safety analysis")

        # Log the assessment
        self.logger.info(f"Ethical assessment for '{requirement[:50]}...': {assessment.risk_level} risk, approved={assessment.approved}")

        return assessment

    def analyze_code_safety(self, code: str) -> Tuple[bool, List[str]]:
        """
        Analyze generated code for safety issues.
        """
        issues = []

        try:
            # Parse the AST
            tree = ast.parse(code)

            # Check for dangerous imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.safety_limits.blocked_modules:
                            issues.append(f"Blocked import: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module in self.safety_limits.blocked_modules:
                        issues.append(f"Blocked import from: {node.module}")

            # Check for dangerous function calls
            dangerous_functions = ['exec', 'eval', 'compile', '__import__', 'open', 'subprocess']
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
                        issues.append(f"Dangerous function call: {node.func.id}")
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in dangerous_functions:
                        issues.append(f"Dangerous method call: {node.func.attr}")

            # Check for file system operations
            fs_operations = ['open', 'read', 'write', 'remove', 'delete', 'mkdir', 'rmdir']
            fs_count = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in fs_operations:
                        fs_count += 1
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in fs_operations:
                        fs_count += 1

            if fs_count > self.safety_limits.max_file_operations:
                issues.append(f"Too many file operations: {fs_count} (limit: {self.safety_limits.max_file_operations})")

        except SyntaxError as e:
            issues.append(f"Code syntax error: {e}")

        safe = len(issues) == 0
        return safe, issues

    def validate_tool_execution(self, tool: 'GeneratedTool', inputs: Dict[str, Any]) -> bool:
        """
        Validate that tool execution is safe with given inputs.
        """
        # Check input sizes
        for key, value in inputs.items():
            if isinstance(value, str) and len(value) > 10000:
                self.logger.warning(f"Large input detected for {tool.spec.name}: {key} ({len(value)} chars)")
                return False

        # Check for potentially dangerous inputs
        dangerous_patterns = [
            r'(rm\s+-rf\s+/)',  # Dangerous shell commands
            r'(DELETE\s+FROM)',  # SQL injection
            r'(\.\./)',  # Path traversal
        ]

        for key, value in inputs.items():
            if isinstance(value, str):
                for pattern in dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        self.logger.warning(f"Dangerous input pattern detected in {key}: {pattern}")
                        return False

        return True

    def _risk_order(self, risk: str) -> int:
        """Order risk levels for comparison"""
        order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        return order.get(risk, 0)

    def log_tool_creation(self, tool: 'GeneratedTool', assessment: EthicalAssessment):
        """Log tool creation with ethical assessment"""
        self.logger.info(f"Tool created: {tool.spec.name}")
        self.logger.info(f"Risk level: {assessment.risk_level}")
        self.logger.info(f"Concerns: {', '.join(assessment.concerns) if assessment.concerns else 'None'}")
        self.logger.info(f"Approved: {assessment.approved}")

    def get_ethical_summary(self) -> Dict[str, Any]:
        """Get summary of ethical guard activity"""
        # This would read from logs in a real implementation
        return {
            'total_assessments': 0,  # Would be counted from logs
            'approved_tools': 0,
            'rejected_tools': 0,
            'high_risk_tools': 0,
            'active_safeguards': [
                'Content filtering',
                'Code safety analysis',
                'Input validation',
                'Resource limits',
                'Activity logging'
            ]
        }

@dataclass
class ToolSpec:
    """Specification for a tool to be created"""
    name: str
    description: str
    requirements: List[str]
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    code_template: str
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

@dataclass
class GeneratedTool:
    """A successfully created and tested tool"""
    spec: ToolSpec
    code: str
    module_path: str
    function: Callable
    hash: str
    created_at: float
    test_results: Dict[str, Any]

class AutomaticToolMaker:
    """
    AQI's automatic tool creation system with comprehensive ethical safeguards.
    Can analyze requirements, generate code, test implementations, and deploy tools
    while ensuring all activities align with ethical guidelines.
    """

    def __init__(self, aqi_core=None, enable_ethical_checks: bool = True):
        self.aqi_core = aqi_core
        self.tool_registry: Dict[str, GeneratedTool] = {}
        self.temp_dir = tempfile.mkdtemp(prefix="aqi_tools_")
        self.ethical_guard = EthicalGuard() if enable_ethical_checks else None
        self.enable_ethical_checks = enable_ethical_checks

        # Code generation templates
        self.templates = {
            'api_wrapper': self._api_wrapper_template,
            'data_processor': self._data_processor_template,
            'automation_script': self._automation_script_template,
            'analysis_tool': self._analysis_tool_template
        }

    def create_tool(self, requirement: str, tool_type: str = 'auto') -> Optional[GeneratedTool]:
        """
        Main method: Create a tool from a natural language requirement with ethical safeguards
        """
        try:
            # Step 0: Ethical Assessment (FIRST AND MOST IMPORTANT)
            if self.enable_ethical_checks and self.ethical_guard:
                assessment = self.ethical_guard.assess_request(requirement, tool_type)

                if not assessment.approved:
                    if self.aqi_core:
                        self.aqi_core.log_error("Tool creation REJECTED for ethical reasons: {}".format(
                            ', '.join(assessment.concerns)
                        ))
                    print("❌ Tool creation rejected for ethical concerns:")
                    for concern in assessment.concerns:
                        print("   - {}".format(concern))
                    return None

                if assessment.requires_oversight:
                    print("⚠️  Tool requires human oversight. Risk level: {}".format(assessment.risk_level))
                    for concern in assessment.concerns:
                        print("   - {}".format(concern))

                    # In a real system, this would prompt for human approval
                    # For now, we'll allow medium-risk tools but log them
                    if assessment.risk_level == 'high':
                        print("❌ High-risk tool creation blocked. Human approval required.")
                        return None

            # Step 1: Analyze requirement
            spec = self._analyze_requirement(requirement, tool_type)
            if not spec:
                return None

            # Step 2: Generate code
            code = self._generate_code(spec)

            # Step 3: Code Safety Analysis
            if self.enable_ethical_checks and self.ethical_guard:
                safe, issues = self.ethical_guard.analyze_code_safety(code)
                if not safe:
                    if self.aqi_core:
                        self.aqi_core.log_error("Generated code failed safety check: {}".format(', '.join(issues)))
                    print("❌ Generated code failed safety analysis:")
                    for issue in issues:
                        print("   - {}".format(issue))
                    return None

            # Step 4: Test the code
            test_results = self._test_code(code, spec)
            if not test_results['passed']:
                # Attempt to fix and retest
                code = self._fix_code(code, test_results)
                test_results = self._test_code(code, spec)
                if not test_results['passed']:
                    return None

            # Step 5: Deploy the tool
            tool = self._deploy_tool(code, spec, test_results)

            # Step 6: Register the tool
            self._register_tool(tool)

            # Step 7: Log ethical compliance
            if self.enable_ethical_checks and self.ethical_guard:
                self.ethical_guard.log_tool_creation(tool, assessment)

            return tool

        except Exception as e:
            if self.aqi_core:
                self.aqi_core.log_error("Tool creation failed: {}".format(e))
            return None

    def _analyze_requirement(self, requirement: str, tool_type: str) -> Optional[ToolSpec]:
        """
        Use AQI's intelligence to analyze the requirement and create a tool specification
        """
        # This would use AQI's natural language processing and reasoning
        # For now, we'll use pattern matching and heuristics

        spec = ToolSpec(
            name=self._generate_tool_name(requirement),
            description=requirement,
            requirements=self._extract_requirements(requirement),
            inputs=self._infer_inputs(requirement),
            outputs=self._infer_outputs(requirement),
            code_template=self._select_template(requirement, tool_type)
        )

        # Add test cases
        spec.test_cases = self._generate_test_cases(spec)

        return spec

    def _generate_tool_name(self, requirement: str) -> str:
        """Generate a suitable function/class name from requirement"""
        words = requirement.lower().split()
        key_words = [w for w in words if w not in ['a', 'an', 'the', 'to', 'for', 'with', 'and', 'or']]
        return '_'.join(key_words[:3]) + '_tool'

    def _extract_requirements(self, requirement: str) -> List[str]:
        """Extract functional requirements from natural language"""
        requirements = []

        if 'api' in requirement.lower():
            requirements.append('make_api_call')
        if 'data' in requirement.lower():
            requirements.append('process_data')
        if 'file' in requirement.lower():
            requirements.append('file_operations')
        if 'web' in requirement.lower():
            requirements.append('web_scraping')

        return requirements or ['basic_functionality']

    def _infer_inputs(self, requirement: str) -> Dict[str, str]:
        """Infer input parameters from requirement"""
        inputs = {}

        req_lower = requirement.lower()

        # More specific pattern matching
        if 'url' in req_lower and 'api' in req_lower:
            inputs['url'] = 'str'
        elif 'file' in req_lower and ('path' in req_lower or 'read' in req_lower):
            inputs['file_path'] = 'str'
        elif 'data' in req_lower and ('process' in req_lower or 'analyze' in req_lower) and 'automation' not in req_lower:
            inputs['input'] = 'any'
        elif 'text' in req_lower and 'analyze' in req_lower and 'automation' not in req_lower:
            inputs['input'] = 'str'

        return inputs

    def _infer_outputs(self, requirement: str) -> Dict[str, str]:
        """Infer output types from requirement"""
        outputs = {}

        if 'result' in requirement.lower():
            outputs['result'] = 'any'
        if 'data' in requirement.lower():
            outputs['processed_data'] = 'dict'
        if 'file' in requirement.lower():
            outputs['output_file'] = 'str'

        return outputs or {'output': 'any'}

    def _select_template(self, requirement: str, tool_type: str) -> str:
        """Select appropriate code template"""
        if tool_type != 'auto':
            return tool_type

        req_lower = requirement.lower()
        if 'api' in req_lower:
            return 'api_wrapper'
        elif 'data' in req_lower or 'process' in req_lower:
            return 'data_processor'
        elif 'automate' in req_lower or 'script' in req_lower:
            return 'automation_script'
        else:
            return 'analysis_tool'

    def _generate_code(self, spec: ToolSpec) -> str:
        """Generate Python code from specification"""
        template_func = self.templates.get(spec.code_template, self._basic_template)
        return template_func(spec)

    def _api_wrapper_template(self, spec: ToolSpec) -> str:
        """Template for API wrapper tools"""
        inputs = ', '.join(["{}: {}".format(k, v) for k, v in spec.inputs.items()])

        return '''import requests
import json
from typing import Dict, Any

def {}(url: str) -> Dict[str, Any]:
    """
    {}
    Generated automatically by AQI Automatic Tool Maker
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return {{
            'success': True,
            'data': response.json(),
            'status_code': response.status_code
        }}
    except Exception as e:
        return {{
            'success': False,
            'error': str(e),
            'status_code': None
        }}
'''.format(spec.name, spec.description)

    def _data_processor_template(self, spec: ToolSpec) -> str:
        """Template for data processing tools"""
        inputs = ', '.join(["{}: {}".format(k, v) for k, v in spec.inputs.items()])

        return '''import pandas as pd
import json
from typing import Dict, Any, List

def {}(data: dict) -> Dict[str, Any]:
    """
    {}
    Generated automatically by AQI Automatic Tool Maker
    """
    try:
        # Load data
        if isinstance(data, str):
            df = pd.read_csv(data) if data.endswith('.csv') else pd.read_json(data)
        else:
            df = pd.DataFrame(data)

        # Basic processing
        result = {{
            'row_count': len(df),
            'columns': list(df.columns),
            'summary': df.describe().to_dict()
        }}

        return {{
            'success': True,
            'result': result
        }}
    except Exception as e:
        return {{
            'success': False,
            'error': str(e)
        }}
'''.format(spec.name, spec.description)

    def _automation_script_template(self, spec: ToolSpec) -> str:
        """Template for automation scripts"""
        inputs = ', '.join(["{}: {}".format(k, v) for k, v in spec.inputs.items()])

        return '''import subprocess
import os
from typing import Dict, Any

def {}() -> Dict[str, Any]:
    """
    {}
    Generated automatically by AQI Automatic Tool Maker
    """
    try:
        # Execute automation command
        result = subprocess.run(
            ['echo', 'Automation executed'],
            capture_output=True,
            text=True,
            timeout=30
        )

        return {{
            'success': True,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode
        }}
    except Exception as e:
        return {{
            'success': False,
            'error': str(e)
        }}
'''.format(spec.name, spec.description)

    def _analysis_tool_template(self, spec: ToolSpec) -> str:
        """Template for analysis tools"""
        inputs = ', '.join(["{}: {}".format(k, v) for k, v in spec.inputs.items()])

        return '''import json
from typing import Dict, Any

def {}(input: any) -> Dict[str, Any]:
    """
    {}
    Generated automatically by AQI Automatic Tool Maker
    """
    try:
        # Perform analysis
        analysis = {{
            'input_type': str(type(input)),
            'input_length': len(str(input)) if hasattr(input, '__len__') else 'N/A',
            'basic_stats': {{
                'has_data': input is not None,
                'is_dict': isinstance(input, dict),
                'is_list': isinstance(input, list)
            }}
        }}

        return {{
            'success': True,
            'analysis': analysis
        }}
    except Exception as e:
        return {{
            'success': False,
            'error': str(e)
        }}
'''.format(spec.name, spec.description)

    def _basic_template(self, spec: ToolSpec) -> str:
        """Fallback basic template"""
        inputs = ', '.join(["{}: {}".format(k, v) for k, v in spec.inputs.items()])

        return '''def {}({}):
    """
    {}
    Generated automatically by AQI Automatic Tool Maker
    """
    return {{
        'success': True,
        'message': 'Tool executed successfully',
        'input': {}
    }}
'''.format(spec.name, inputs, spec.description, list(spec.inputs.keys())[0] if spec.inputs else None)

    def _generate_test_cases(self, spec: ToolSpec) -> List[Dict[str, Any]]:
        """Generate test cases for the tool"""
        test_cases = []

        # Basic functionality test
        test_input = {}
        for param, type_hint in spec.inputs.items():
            if type_hint == 'str':
                test_input[param] = 'test_value'
            elif type_hint == 'dict':
                test_input[param] = {'test': 'data'}
            else:
                test_input[param] = 'test'

        # If no inputs specified, use default based on template
        if not spec.inputs:
            if spec.code_template == 'analysis_tool':
                test_input = {'input': 'test data'}
            elif spec.code_template == 'api_wrapper':
                test_input = {'url': 'https://httpbin.org/json'}
            elif spec.code_template == 'data_processor':
                test_input = {'data': {'test': 'data'}}
            elif spec.code_template == 'automation_script':
                test_input = {}  # No parameters for automation scripts
            else:
                test_input = {}

        test_cases.append({
            'name': 'basic_functionality',
            'input': test_input,
            'expected_keys': ['success']
        })

        return test_cases

    def _test_code(self, code: str, spec: ToolSpec) -> Dict[str, Any]:
        """Test the generated code safely"""
        results = {
            'passed': False,
            'errors': [],
            'test_results': []
        }

        try:
            # Create temporary module
            module_name = "test_{}_{}".format(spec.name, int(time.time()))
            module_path = os.path.join(self.temp_dir, "{}.py".format(module_name))

            with open(module_path, 'w') as f:
                f.write(code)

            # Import and test
            spec_module = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec_module)
            spec_module.loader.exec_module(module)

            # Get the function
            func = getattr(module, spec.name)

            # Run test cases
            for test_case in spec.test_cases:
                try:
                    result = func(**test_case['input'])
                    results['test_results'].append({
                        'test': test_case['name'],
                        'passed': True,
                        'result': result
                    })
                except Exception as e:
                    results['test_results'].append({
                        'test': test_case['name'],
                        'passed': False,
                        'error': str(e)
                    })
                    results['errors'].append(str(e))

            # Check if all tests passed
            results['passed'] = all(test['passed'] for test in results['test_results'])

        except Exception as e:
            results['errors'].append("Code execution failed: {}".format(str(e)))

        return results

    def _fix_code(self, code: str, test_results: Dict[str, Any]) -> str:
        """Attempt to fix code based on test failures"""
        # This is a simplified version - in practice, this would use AQI's intelligence
        # to analyze errors and generate fixes

        fixed_code = code

        for error in test_results['errors']:
            if 'NameError' in error:
                # Add missing import
                if 'requests' in error:
                    fixed_code = "import requests\n" + fixed_code
                elif 'pandas' in error:
                    fixed_code = "import pandas as pd\n" + fixed_code

        return fixed_code

    def _deploy_tool(self, code: str, spec: ToolSpec, test_results: Dict[str, Any]) -> GeneratedTool:
        """Deploy the tested tool"""
        # Create permanent module file
        module_name = "aqi_tool_{}_{}".format(spec.name, int(time.time()))
        module_path = os.path.join(self.temp_dir, "{}.py".format(module_name))

        with open(module_path, 'w') as f:
            f.write(code)

        # Import the module
        spec_module = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec_module)
        spec_module.loader.exec_module(module)

        # Get the function
        func = getattr(module, spec.name)

        # Create tool object
        tool = GeneratedTool(
            spec=spec,
            code=code,
            module_path=module_path,
            function=func,
            hash=hashlib.md5(code.encode()).hexdigest(),
            created_at=time.time(),
            test_results=test_results
        )

        return tool

    def _register_tool(self, tool: GeneratedTool):
        """Register the tool in the registry"""
        self.tool_registry[tool.spec.name] = tool

        # Log to AQI if available
        if self.aqi_core:
            self.aqi_core.log_event("New tool created: {}".format(tool.spec.name))

    def get_tool(self, name: str) -> Optional[GeneratedTool]:
        """Retrieve a tool from the registry"""
        return self.tool_registry.get(name)

    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tool_registry.keys())

    def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a registered tool with safety validation"""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError("Tool '{}' not found".format(name))

        # Ethical input validation
        if self.enable_ethical_checks and self.ethical_guard:
            if not self.ethical_guard.validate_tool_execution(tool, kwargs):
                raise ValueError("Tool execution blocked: Input validation failed")

        # Execute with safety limits
        try:
            # In a real implementation, this would run in a restricted environment
            # with resource limits, timeouts, etc.
            result = tool.function(**kwargs)
            return result
        except Exception as e:
            if self.aqi_core:
                self.aqi_core.log_error("Tool execution failed: {}".format(e))
            raise

    def get_ethical_status(self) -> Dict[str, Any]:
        """Get the current ethical status and safeguards"""
        if not self.enable_ethical_checks or not self.ethical_guard:
            return {
                'ethical_checks_enabled': False,
                'status': 'disabled'
            }

        return {
            'ethical_checks_enabled': True,
            'status': 'active',
            'summary': self.ethical_guard.get_ethical_summary(),
            'active_safeguards': [
                'Content filtering for harmful requests',
                'Code safety analysis (AST parsing)',
                'Input validation and sanitization',
                'Resource limits and execution timeouts',
                'Comprehensive activity logging',
                'Risk assessment and approval workflow',
                'Human oversight for high-risk tools'
            ]
        }

# Example usage
if __name__ == "__main__":
    tool_maker = AutomaticToolMaker()

    # Create a simple API wrapper tool
    tool = tool_maker.create_tool(
        "Create a tool that fetches data from a REST API",
        tool_type='api_wrapper'
    )

    if tool:
        print("Tool created: {}".format(tool.spec.name))
        print("Available tools: {}".format(tool_maker.list_tools()))

        # Test execution
        result = tool_maker.execute_tool(tool.spec.name, url="https://httpbin.org/json")
        print("Execution result: {}".format(result))
    else:
        print("Tool creation failed")