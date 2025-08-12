"""MCP (Model Context Protocol) Manager for HubSpot Integration"""

import json
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput, ApiException
from hubspot.crm.deals import SimplePublicObjectInput as DealInput
from hubspot.crm.objects.meetings import SimplePublicObjectInput as MeetingInput

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StudentProfile:
    """Student profile from HubSpot"""
    contact_id: str
    email: str
    student_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    course: Optional[str]
    year_of_study: Optional[int]
    campus: Optional[str]
    preferences: Dict[str, Any]
    last_interaction: Optional[datetime]
    interaction_count: int


@dataclass
class MeetingSlot:
    """Available meeting slot"""
    start_time: datetime
    end_time: datetime
    agent_name: str
    agent_email: str
    meeting_type: str
    location: str


@dataclass
class MCPResponse:
    """MCP service response"""
    success: bool
    data: Any
    message: str
    error: Optional[str] = None


class MCPManager:
    """MCP Manager for HubSpot integration and student personalization"""
    
    def __init__(self):
        self.hubspot_client = None
        self.mcp_server_url = settings.HUBSPOT_MCP_SERVER_URL
        self.session = None
    
    async def initialize(self):
        """Initialize MCP Manager and HubSpot client"""
        try:
            # Initialize HubSpot client
            self.hubspot_client = HubSpot(access_token=settings.HUBSPOT_API_KEY)
            
            # Initialize HTTP session for MCP server communication
            self.session = aiohttp.ClientSession()
            
            # Test HubSpot connection
            await self._test_hubspot_connection()
            
            logger.info("MCP Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"MCP Manager initialization failed: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def get_student_profile(self, whatsapp_id: str, email: Optional[str] = None) -> Optional[StudentProfile]:
        """Get or create student profile from HubSpot"""
        try:
            contact = None
            
            # Search by email first if provided
            if email:
                contact = await self._search_contact_by_email(email)
            
            # If not found by email, search by custom WhatsApp ID field
            if not contact:
                contact = await self._search_contact_by_whatsapp_id(whatsapp_id)
            
            # If still not found, create new contact
            if not contact:
                contact = await self._create_student_contact(whatsapp_id, email)
            
            if contact:
                return await self._parse_student_profile(contact)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get student profile: {e}")
            return None
    
    async def update_student_interaction(self, whatsapp_id: str, interaction_data: Dict):
        """Update student interaction history in HubSpot"""
        try:
            contact = await self._search_contact_by_whatsapp_id(whatsapp_id)
            
            if contact:
                # Update interaction count and last interaction date
                current_count = int(contact.properties.get('interaction_count', 0))
                
                properties = {
                    'last_interaction_date': datetime.utcnow().isoformat(),
                    'interaction_count': str(current_count + 1),
                    'last_interaction_type': interaction_data.get('type', 'whatsapp_chat'),
                    'last_interaction_topic': interaction_data.get('topic', ''),
                    'satisfaction_score': interaction_data.get('satisfaction', '')
                }
                
                # Update contact
                await self._update_contact(contact.id, properties)
                
                # Create interaction note
                await self._create_interaction_note(contact.id, interaction_data)
                
                logger.info(f"Updated interaction for student: {whatsapp_id}")
        
        except Exception as e:
            logger.error(f"Failed to update student interaction: {e}")
    
    async def schedule_meeting(self, whatsapp_id: str, meeting_request: Dict) -> MCPResponse:
        """Schedule a meeting with UWS agent"""
        try:
            # Get student profile
            student = await self._search_contact_by_whatsapp_id(whatsapp_id)
            if not student:
                return MCPResponse(
                    success=False,
                    data=None,
                    message="Student profile not found",
                    error="PROFILE_NOT_FOUND"
                )
            
            # Get available meeting slots
            available_slots = await self._get_available_meeting_slots(
                meeting_type=meeting_request.get('type', 'academic_support'),
                campus=meeting_request.get('campus'),
                preferred_date=meeting_request.get('preferred_date')
            )
            
            if not available_slots:
                return MCPResponse(
                    success=False,
                    data=None,
                    message="No available meeting slots found",
                    error="NO_SLOTS_AVAILABLE"
                )
            
            # Create meeting in HubSpot
            meeting_data = {
                'properties': {
                    'hs_meeting_title': f"Student Support - {student.properties.get('firstname', 'Student')}",
                    'hs_meeting_body': meeting_request.get('description', ''),
                    'hs_meeting_start_time': available_slots[0].start_time.isoformat(),
                    'hs_meeting_end_time': available_slots[0].end_time.isoformat(),
                    'hs_meeting_location': available_slots[0].location,
                    'meeting_type': available_slots[0].meeting_type,
                    'student_whatsapp_id': whatsapp_id
                },
                'associations': [
                    {
                        'to': {'id': student.id},
                        'types': [{'associationCategory': 'HUBSPOT_DEFINED', 'associationTypeId': 198}]
                    }
                ]
            }
            
            meeting = await self._create_meeting(meeting_data)
            
            if meeting:
                return MCPResponse(
                    success=True,
                    data={
                        'meeting_id': meeting.id,
                        'start_time': available_slots[0].start_time.isoformat(),
                        'end_time': available_slots[0].end_time.isoformat(),
                        'agent_name': available_slots[0].agent_name,
                        'location': available_slots[0].location,
                        'meeting_link': f"https://app.hubspot.com/meetings/{settings.HUBSPOT_PORTAL_ID}/{meeting.id}"
                    },
                    message="Meeting scheduled successfully"
                )
            
            return MCPResponse(
                success=False,
                data=None,
                message="Failed to create meeting",
                error="MEETING_CREATION_FAILED"
            )
            
        except Exception as e:
            logger.error(f"Failed to schedule meeting: {e}")
            return MCPResponse(
                success=False,
                data=None,
                message="Internal error occurred",
                error=str(e)
            )
    
    async def get_personalized_recommendations(self, whatsapp_id: str, context: Dict) -> List[str]:
        """Get personalized recommendations based on student profile"""
        try:
            student = await self.get_student_profile(whatsapp_id)
            
            if not student:
                return self._get_default_recommendations()
            
            recommendations = []
            
            # Course-specific recommendations
            if student.course:
                recommendations.extend(self._get_course_recommendations(student.course))
            
            # Campus-specific recommendations
            if student.campus:
                recommendations.extend(self._get_campus_recommendations(student.campus))
            
            # Year of study recommendations
            if student.year_of_study:
                recommendations.extend(self._get_year_recommendations(student.year_of_study))
            
            # Based on interaction history
            if student.last_interaction:
                recommendations.extend(self._get_interaction_recommendations(student))
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Failed to get personalized recommendations: {e}")
            return self._get_default_recommendations()
    
    async def _test_hubspot_connection(self):
        """Test HubSpot API connection"""
        try:
            # Try to get account info
            account_info = self.hubspot_client.auth.oauth.access_tokens_api.get_access_token()
            logger.info("HubSpot connection test successful")
            
        except Exception as e:
            logger.error(f"HubSpot connection test failed: {e}")
            raise
    
    async def _search_contact_by_email(self, email: str):
        """Search contact by email"""
        try:
            search_request = {
                'filterGroups': [{
                    'filters': [{
                        'propertyName': 'email',
                        'operator': 'EQ',
                        'value': email
                    }]
                }],
                'properties': ['firstname', 'lastname', 'email', 'student_id', 'course', 
                              'year_of_study', 'campus', 'whatsapp_id', 'interaction_count',
                              'last_interaction_date', 'preferences']
            }
            
            result = self.hubspot_client.crm.contacts.search_api.do_search(search_request)
            
            return result.results[0] if result.results else None
            
        except Exception as e:
            logger.error(f"Error searching contact by email: {e}")
            return None
    
    async def _search_contact_by_whatsapp_id(self, whatsapp_id: str):
        """Search contact by WhatsApp ID"""
        try:
            search_request = {
                'filterGroups': [{
                    'filters': [{
                        'propertyName': 'whatsapp_id',
                        'operator': 'EQ',
                        'value': whatsapp_id
                    }]
                }],
                'properties': ['firstname', 'lastname', 'email', 'student_id', 'course', 
                              'year_of_study', 'campus', 'whatsapp_id', 'interaction_count',
                              'last_interaction_date', 'preferences']
            }
            
            result = self.hubspot_client.crm.contacts.search_api.do_search(search_request)
            
            return result.results[0] if result.results else None
            
        except Exception as e:
            logger.error(f"Error searching contact by WhatsApp ID: {e}")
            return None
    
    async def _create_student_contact(self, whatsapp_id: str, email: Optional[str] = None):
        """Create new student contact in HubSpot"""
        try:
            properties = {
                'whatsapp_id': whatsapp_id,
                'contact_source': 'whatsapp_bot',
                'interaction_count': '0',
                'first_interaction_date': datetime.utcnow().isoformat(),
                'lifecycle_stage': 'student'
            }
            
            if email:
                properties['email'] = email
            
            contact_input = SimplePublicObjectInput(properties=properties)
            
            result = self.hubspot_client.crm.contacts.basic_api.create(contact_input)
            
            logger.info(f"Created new student contact: {whatsapp_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating student contact: {e}")
            return None
    
    async def _parse_student_profile(self, contact) -> StudentProfile:
        """Parse HubSpot contact to StudentProfile"""
        props = contact.properties
        
        # Parse last interaction date
        last_interaction = None
        if props.get('last_interaction_date'):
            try:
                last_interaction = datetime.fromisoformat(props['last_interaction_date'])
            except (ValueError, TypeError):
                pass
        
        # Parse preferences
        preferences = {}
        if props.get('preferences'):
            try:
                preferences = json.loads(props['preferences'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        return StudentProfile(
            contact_id=contact.id,
            email=props.get('email', ''),
            student_id=props.get('student_id'),
            first_name=props.get('firstname'),
            last_name=props.get('lastname'),
            course=props.get('course'),
            year_of_study=int(props.get('year_of_study', 0)) if props.get('year_of_study') else None,
            campus=props.get('campus'),
            preferences=preferences,
            last_interaction=last_interaction,
            interaction_count=int(props.get('interaction_count', 0))
        )
    
    def _get_default_recommendations(self) -> List[str]:
        """Get default recommendations for new students"""
        return [
            "Check your course timetable on the student portal",
            "Visit the library for study resources and quiet spaces",
            "Join student societies to meet new people",
            "Explore campus facilities and services",
            "Contact student services if you need any support"
        ]
    
    def _get_course_recommendations(self, course: str) -> List[str]:
        """Get course-specific recommendations"""
        course_lower = course.lower()
        
        if 'computer' in course_lower or 'computing' in course_lower:
            return [
                "Check out the latest programming workshops in the computing lab",
                "Join the Computing Society for networking and tech talks",
                "Access online coding resources through the library portal"
            ]
        elif 'business' in course_lower:
            return [
                "Attend business networking events organized by the Business School",
                "Use the Bloomberg terminals in the business lab",
                "Check career services for internship opportunities"
            ]
        elif 'engineering' in course_lower:
            return [
                "Book time in the engineering workshops for practical projects",
                "Join the Engineering Society for industry connections",
                "Access CAD software through the computing facilities"
            ]
        
        return []
    
    def _get_campus_recommendations(self, campus: str) -> List[str]:
        """Get campus-specific recommendations"""
        campus_lower = campus.lower()
        
        if 'paisley' in campus_lower:
            return [
                "Visit the Paisley campus library for extended study hours",
                "Check out the sports facilities at the Paisley campus",
                "Join campus events at the Paisley Student Union"
            ]
        elif 'ayr' in campus_lower:
            return [
                "Explore the coastal location advantages for outdoor activities",
                "Use the specialized facilities at Ayr campus",
                "Connect with the tight-knit Ayr campus community"
            ]
        
        return []
    
    def _get_year_recommendations(self, year: int) -> List[str]:
        """Get year-specific recommendations"""
        if year == 1:
            return [
                "Attend the first-year orientation events",
                "Join study groups to build friendships",
                "Familiarize yourself with campus resources"
            ]
        elif year >= 3:
            return [
                "Start planning for your final year project",
                "Visit career services for job search support",
                "Consider graduate program options"
            ]
        
        return []
    
    def _get_interaction_recommendations(self, student: StudentProfile) -> List[str]:
        """Get recommendations based on interaction history"""
        recommendations = []
        
        # If low interaction count, suggest engagement
        if student.interaction_count < 3:
            recommendations.append("Explore more university services through this chat")
        
        # If haven't interacted recently, suggest check-in
        if student.last_interaction:
            days_since = (datetime.utcnow() - student.last_interaction).days
            if days_since > 7:
                recommendations.append("Check for any new announcements or updates")
        
        return recommendations
    
    async def _get_available_meeting_slots(self, meeting_type: str, 
                                         campus: Optional[str], 
                                         preferred_date: Optional[str]) -> List[MeetingSlot]:
        """Get available meeting slots (mock implementation)"""
        # This would typically integrate with a calendar system
        # For demo purposes, returning mock data
        
        base_date = datetime.utcnow() + timedelta(days=1)
        
        return [
            MeetingSlot(
                start_time=base_date.replace(hour=10, minute=0),
                end_time=base_date.replace(hour=11, minute=0),
                agent_name="Dr. Sarah Wilson",
                agent_email="s.wilson@uws.ac.uk",
                meeting_type=meeting_type,
                location="Student Services Office, Paisley Campus"
            ),
            MeetingSlot(
                start_time=base_date.replace(hour=14, minute=0),
                end_time=base_date.replace(hour=15, minute=0),
                agent_name="James Mitchell",
                agent_email="j.mitchell@uws.ac.uk",
                meeting_type=meeting_type,
                location="Academic Support Centre, Ayr Campus"
            )
        ]
    
    async def _create_meeting(self, meeting_data: Dict):
        """Create meeting in HubSpot"""
        try:
            meeting_input = MeetingInput(
                properties=meeting_data['properties'],
                associations=meeting_data.get('associations', [])
            )
            
            result = self.hubspot_client.crm.objects.meetings.basic_api.create(meeting_input)
            return result
            
        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            return None
    
    async def _update_contact(self, contact_id: str, properties: Dict):
        """Update contact properties"""
        try:
            contact_input = SimplePublicObjectInput(properties=properties)
            self.hubspot_client.crm.contacts.basic_api.update(contact_id, contact_input)
            
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
    
    async def _create_interaction_note(self, contact_id: str, interaction_data: Dict):
        """Create interaction note in HubSpot"""
        try:
            # This would create a note or activity in HubSpot
            # Implementation depends on specific HubSpot API endpoints
            pass
            
        except Exception as e:
            logger.error(f"Error creating interaction note: {e}")