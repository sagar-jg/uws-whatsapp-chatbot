"""Guardrails Engine for UWS Academic Content Filtering"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from src.utils.logger import get_logger
from src.database.models import GuardrailLog
from src.database.connection import AsyncSessionLocal

logger = get_logger(__name__)


class ViolationType(Enum):
    """Types of guardrail violations"""
    OFF_TOPIC = "off_topic"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    NON_ACADEMIC = "non_academic"
    PERSONAL_INFO_REQUEST = "personal_info_request"
    EXTERNAL_SERVICE = "external_service"
    HARMFUL_CONTENT = "harmful_content"


class Severity(Enum):
    """Severity levels for violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Action(Enum):
    """Actions to take on violations"""
    ALLOW = "allow"
    WARN = "warn"
    REDIRECT = "redirect"
    BLOCK = "block"


@dataclass
class GuardrailRule:
    """Guardrail rule definition"""
    name: str
    violation_type: ViolationType
    severity: Severity
    action: Action
    patterns: List[str]
    description: str
    redirect_message: Optional[str] = None


@dataclass
class GuardrailResult:
    """Result of guardrail evaluation"""
    is_allowed: bool
    violations: List[ViolationType]
    severity: Severity
    action: Action
    message: str
    confidence: float
    triggered_rules: List[str]


class GuardrailsEngine:
    """Advanced guardrails engine for UWS academic content filtering"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        self.academic_keywords = self._load_academic_keywords()
        self.uws_keywords = self._load_uws_keywords()
    
    def _initialize_rules(self) -> List[GuardrailRule]:
        """Initialize all guardrail rules"""
        return [
            # Off-topic content rules
            GuardrailRule(
                name="non_academic_topics",
                violation_type=ViolationType.OFF_TOPIC,
                severity=Severity.MEDIUM,
                action=Action.REDIRECT,
                patterns=[
                    r"\b(weather|sports|entertainment|celebrity|gossip|politics|news)\b",
                    r"\b(shopping|buying|selling|price|cost|money)\b(?!.*\b(tuition|fees|scholarship)\b)",
                    r"\b(dating|relationship|personal|private|family)\b",
                    r"\b(job|career|employment)\b(?!.*\b(career services|placement|internship)\b)",
                    r"\b(travel|vacation|holiday)\b(?!.*\b(study abroad|exchange)\b)"
                ],
                description="Topics not related to UWS academic matters",
                redirect_message="I'm here to help with UWS academic topics, courses, and university services. How can I assist you with your studies?"
            ),
            
            # Personal information requests
            GuardrailRule(
                name="personal_info_fishing",
                violation_type=ViolationType.PERSONAL_INFO_REQUEST,
                severity=Severity.HIGH,
                action=Action.BLOCK,
                patterns=[
                    r"\b(password|pin|social security|bank|credit card|personal details)\b",
                    r"\b(home address|phone number|email password|login credentials)\b",
                    r"what.*(password|pin|address|phone)",
                    r"(give me|tell me|share).*(personal|private|confidential)"
                ],
                description="Requests for personal or sensitive information",
                redirect_message="I cannot and will not ask for or handle personal sensitive information. For account-related issues, please contact UWS student services directly."
            ),
            
            # Inappropriate content
            GuardrailRule(
                name="inappropriate_content",
                violation_type=ViolationType.INAPPROPRIATE_CONTENT,
                severity=Severity.CRITICAL,
                action=Action.BLOCK,
                patterns=[
                    r"\b(hate|harassment|discrimination|offensive|inappropriate)\b",
                    r"\b(violent|harm|threat|abuse)\b",
                    r"\b(illegal|drugs|alcohol)\b(?!.*\b(policy|regulation|academic)\b)"
                ],
                description="Inappropriate, harmful, or offensive content",
                redirect_message="I cannot assist with inappropriate content. Please keep our conversation focused on UWS academic topics and services."
            ),
            
            # External service requests
            GuardrailRule(
                name="external_services",
                violation_type=ViolationType.EXTERNAL_SERVICE,
                severity=Severity.MEDIUM,
                action=Action.REDIRECT,
                patterns=[
                    r"\b(google|search|browse|internet|website)\b(?!.*\b(uws|university)\b)",
                    r"\b(book|order|purchase|buy)\b(?!.*\b(textbook|academic|course)\b)",
                    r"\b(call|phone|contact)\b(?!.*\b(uws|university|student services)\b)"
                ],
                description="Requests for external services not related to UWS",
                redirect_message="I can only help with UWS-related academic information and services. For external services, please use appropriate channels."
            ),
            
            # Test and assignment help (academic integrity)
            GuardrailRule(
                name="academic_integrity",
                violation_type=ViolationType.HARMFUL_CONTENT,
                severity=Severity.HIGH,
                action=Action.BLOCK,
                patterns=[
                    r"\b(cheat|cheating|plagiarism|copy|steal)\b",
                    r"(do my|complete my|write my).*(assignment|essay|exam|test|homework)",
                    r"\b(answers to|solutions for).*(exam|test|quiz|assignment)",
                    r"\b(hack|bypass|circumvent).*(system|exam|test)"
                ],
                description="Academic integrity violations",
                redirect_message="I cannot help with academic dishonesty. I'm here to guide you to appropriate UWS resources for legitimate academic support."
            )
        ]
    
    def _load_academic_keywords(self) -> List[str]:
        """Load academic-related keywords"""
        return [
            "course", "module", "lecture", "tutorial", "seminar", "assignment", "exam", "test", "quiz",
            "study", "research", "library", "academic", "degree", "qualification", "credit", "grade",
            "enrollment", "registration", "timetable", "schedule", "syllabus", "curriculum",
            "professor", "lecturer", "tutor", "supervisor", "advisor", "faculty", "department",
            "campus", "building", "classroom", "laboratory", "lab", "workshop", "placement",
            "internship", "thesis", "dissertation", "project", "coursework", "assessment"
        ]
    
    def _load_uws_keywords(self) -> List[str]:
        """Load UWS-specific keywords"""
        return [
            "uws", "university of the west of scotland", "paisley", "ayr", "dumfries", "london",
            "student services", "registry", "admissions", "student union", "accommodation",
            "blackboard", "moodle", "student portal", "library services", "it services",
            "careers service", "counselling", "disability services", "international office",
            "finance office", "graduation", "student card", "student discount", "parking"
        ]
    
    async def evaluate(self, message: str, user_whatsapp_id: str, context: Dict = None) -> GuardrailResult:
        """Evaluate message against all guardrail rules"""
        message_lower = message.lower()
        violations = []
        triggered_rules = []
        max_severity = Severity.LOW
        final_action = Action.ALLOW
        confidence_scores = []
        
        # Check if message contains academic content
        academic_score = self._calculate_academic_relevance(message_lower)
        
        # If academic score is very low, check for off-topic
        if academic_score < 0.3:
            violations.append(ViolationType.OFF_TOPIC)
            triggered_rules.append("low_academic_relevance")
            max_severity = Severity.MEDIUM
            final_action = Action.REDIRECT
        
        # Apply all rules
        for rule in self.rules:
            violation_found, confidence = self._check_rule(message_lower, rule)
            
            if violation_found:
                violations.append(rule.violation_type)
                triggered_rules.append(rule.name)
                confidence_scores.append(confidence)
                
                # Update severity and action based on worst violation
                if rule.severity.value in ["critical", "high"] and max_severity.value in ["low", "medium"]:
                    max_severity = rule.severity
                    final_action = rule.action
                elif rule.severity == Severity.MEDIUM and max_severity == Severity.LOW:
                    max_severity = rule.severity
                    final_action = rule.action
        
        # Calculate overall confidence
        overall_confidence = max(confidence_scores) if confidence_scores else academic_score
        
        # Generate response message
        response_message = self._generate_response_message(violations, triggered_rules)
        
        # Log violation if any
        if violations:
            await self._log_violation(
                user_whatsapp_id=user_whatsapp_id,
                violations=violations,
                message=message,
                triggered_rules=triggered_rules,
                severity=max_severity,
                action=final_action
            )
        
        return GuardrailResult(
            is_allowed=final_action != Action.BLOCK,
            violations=violations,
            severity=max_severity,
            action=final_action,
            message=response_message,
            confidence=overall_confidence,
            triggered_rules=triggered_rules
        )
    
    def _check_rule(self, message: str, rule: GuardrailRule) -> Tuple[bool, float]:
        """Check if a specific rule is violated"""
        violation_count = 0
        total_patterns = len(rule.patterns)
        
        for pattern in rule.patterns:
            if re.search(pattern, message, re.IGNORECASE):
                violation_count += 1
        
        # Calculate confidence based on pattern matches
        confidence = violation_count / total_patterns if total_patterns > 0 else 0
        
        # Consider a rule violated if confidence is above threshold
        is_violated = confidence > 0.3 or violation_count >= 1
        
        return is_violated, confidence
    
    def _calculate_academic_relevance(self, message: str) -> float:
        """Calculate academic relevance score"""
        academic_matches = sum(1 for keyword in self.academic_keywords if keyword in message)
        uws_matches = sum(1 for keyword in self.uws_keywords if keyword in message)
        
        total_keywords = len(self.academic_keywords) + len(self.uws_keywords)
        total_matches = academic_matches + (uws_matches * 2)  # UWS keywords weighted higher
        
        # Calculate relevance score
        relevance_score = min(total_matches / 10, 1.0)  # Normalize to 0-1
        
        return relevance_score
    
    def _generate_response_message(self, violations: List[ViolationType], triggered_rules: List[str]) -> str:
        """Generate appropriate response message based on violations"""
        if not violations:
            return ""
        
        # Priority order for messages
        if ViolationType.INAPPROPRIATE_CONTENT in violations:
            return "I cannot assist with inappropriate content. Please keep our conversation focused on UWS academic topics and services."
        
        if ViolationType.PERSONAL_INFO_REQUEST in violations:
            return "I cannot and will not ask for or handle personal sensitive information. For account-related issues, please contact UWS student services directly."
        
        if ViolationType.HARMFUL_CONTENT in violations:
            return "I cannot help with academic dishonesty. I'm here to guide you to appropriate UWS resources for legitimate academic support."
        
        if ViolationType.OFF_TOPIC in violations or ViolationType.NON_ACADEMIC in violations:
            return "I'm here to help with UWS academic topics, courses, and university services. How can I assist you with your studies?"
        
        if ViolationType.EXTERNAL_SERVICE in violations:
            return "I can only help with UWS-related academic information and services. For external services, please use appropriate channels."
        
        return "I'm designed to help with UWS academic matters. Please ask about courses, university services, or academic support."
    
    async def _log_violation(self, user_whatsapp_id: str, violations: List[ViolationType], 
                           message: str, triggered_rules: List[str], 
                           severity: Severity, action: Action):
        """Log guardrail violation to database"""
        try:
            async with AsyncSessionLocal() as session:
                log_entry = GuardrailLog(
                    user_whatsapp_id=user_whatsapp_id,
                    violation_type=", ".join([v.value for v in violations]),
                    user_message=message,
                    rule_triggered=", ".join(triggered_rules),
                    severity=severity.value,
                    action_taken=action.value,
                    metadata={
                        "violations": [v.value for v in violations],
                        "triggered_rules": triggered_rules,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                session.add(log_entry)
                await session.commit()
                
                logger.info(f"Logged guardrail violation for user {user_whatsapp_id}: {violations}")
                
        except Exception as e:
            logger.error(f"Failed to log guardrail violation: {e}")
    
    def is_uws_related(self, message: str) -> bool:
        """Quick check if message is UWS-related"""
        message_lower = message.lower()
        
        # Check for UWS-specific terms
        uws_indicators = [
            "uws", "university of the west of scotland",
            "paisley", "ayr", "dumfries", "london campus"
        ]
        
        for indicator in uws_indicators:
            if indicator in message_lower:
                return True
        
        # Check for academic terms combined with question words
        academic_terms = ["course", "module", "lecture", "exam", "assignment", "library", "student"]
        question_words = ["what", "when", "where", "how", "can", "is", "are", "do", "does"]
        
        has_academic = any(term in message_lower for term in academic_terms)
        has_question = any(word in message_lower for word in question_words)
        
        return has_academic and has_question