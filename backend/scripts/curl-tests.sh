#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:5000"                                                                       
                                                                                                    
---                                                                                                
Surveys                                                                                            
                                                                                                    
# List surveys in a project                                                                        
curl "$BASE/api/v1/projects/1/surveys"                                                             
                                                                                                    
# Create a survey                                                                                  
curl -X POST "$BASE/api/v1/projects/1/surveys" \                                                   
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "title": "Employee NPS Q2",                                                                    
    "visibility": "link_only",                                                                     
    "allow_public_responses": true                                                                 
}'                                                                                               
                                                                                                    
# Get a survey                                                                                     
curl "$BASE/api/v1/projects/1/surveys/1"                                                           
                                                                                                    
# Update a survey (slug, visibility, etc.)                                                         
curl -X PATCH "$BASE/api/v1/projects/1/surveys/1" \                                                
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "title": "Employee NPS Q2 — Updated",                                                          
    "visibility": "public",                                                                        
    "public_slug": "nps-q2"                                                                        
}'                                                                                               
                                                                                                    
# Delete a survey                                                                                
curl -X DELETE "$BASE/api/v1/projects/1/surveys/1"                                                 
                                                                                                    
---                                                                                                
Versions                                                                                           
                                                                                                    
# List versions                                                                                  
curl "$BASE/api/v1/projects/1/surveys/1/versions"
                                                                                                    
# Create a new draft version (no body required)                                                    
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions" \                                        
-H "Content-Type: application/json" \                                                            
-d '{}'                                                                                          
                                                                                                    
# Get a specific version                                                                           
curl "$BASE/api/v1/projects/1/surveys/1/versions/1"                                              
                                                                                                    
# Archive a version                                                                                
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions/1/archive" \                              
-H "Content-Type: application/json" \                                                            
-d '{}'                                                                                          
                                                                                                
---
Draft content (questions, rules, scoring rules)                                                    
                                                                                                    
# List questions on a draft version                                                                
curl "$BASE/api/v1/projects/1/surveys/1/versions/1/questions"                                      
                                                                                                    
# Add a question                                                                                   
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions/1/questions" \                            
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "question_key": "recommend_score",                                                             
    "question_schema": {                                                                           
    "type": "rating",                                                                            
    "label": "How likely are you to recommend us?",                                              
    "min": 0,                                                                                    
    "max": 10                                                                                    
    }                                                                                              
}'                                                                                               
                                                                                                    
# Add a second question (field type)                                                             
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions/1/questions" \                            
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "question_key": "open_feedback",                                                               
    "question_schema": {                                                                           
    "type": "field",                                                                             
    "label": "Any additional feedback?",                                                         
    "optional": true                                                                             
    }                                                                                            
}'
                                                                                                    
# Update a question                                                                                
curl -X PATCH "$BASE/api/v1/projects/1/surveys/1/versions/1/questions/1" \                         
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "question_schema": {                                                                           
    "type": "rating",                                                                            
    "label": "How likely are you to recommend us? (0–10)",                                       
    "min": 0,                                                                                    
    "max": 10                                                                                    
    }                                                                                              
}'                                                                                               
                                                                                                    
# Delete a question                                                                                
curl -X DELETE "$BASE/api/v1/projects/1/surveys/1/versions/1/questions/2"                        
                                                                                                    
# Add a branching rule                                                                             
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions/1/rules" \                                
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "rule_key": "show_feedback_if_low",                                                            
    "rule_schema": {                                                                               
    "condition": {"question": "recommend_score", "op": "lt", "value": 7},                        
    "action": {"show": "open_feedback"}                                                          
    }                                                                                              
}'                                                                                               
                                                                                                    
# Add a scoring rule                                                                               
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions/1/scoring-rules" \                        
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "scoring_key": "nps_category",                                                                 
    "scoring_schema": {                                                                            
    "source": "recommend_score",                                                                 
    "buckets": [                                                                                 
        {"range": [0, 6], "label": "detractor"},                                                   
        {"range": [7, 8], "label": "passive"},                                                     
        {"range": [9, 10], "label": "promoter"}                                                    
    ]                                                                                            
    }                                                                                              
}'                                                                                               
                                                                                                
---
Publish

# Publish version 1 (must have at least one question)                                              
curl -X POST "$BASE/api/v1/projects/1/surveys/1/versions/1/publish" \                              
-H "Content-Type: application/json" \                                                            
-d '{}'                                                                                          
                                                                                                    
---                                                                                                
Public links                                                                                     

# List links for a survey                                                                          
curl "$BASE/api/v1/projects/1/surveys/1/public-links"                                              
                                                                                                    
# Create a public link (token returned once — save it)                                             
curl -X POST "$BASE/api/v1/projects/1/surveys/1/public-links" \                                    
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "allow_response": true,                                                                        
    "expires_at": null                                                                             
}'                                                                                               
                                                                                                    
# Disable a link                                                                                   
curl -X PATCH "$BASE/api/v1/projects/1/surveys/1/public-links/1" \                                 
-H "Content-Type: application/json" \                                                            
-d '{"is_active": false}'                                                                        
                                                                                                    
# Delete a link                                                                                    
curl -X DELETE "$BASE/api/v1/projects/1/surveys/1/public-links/1"                                  
                                                                                                    
---                                                                                                
Public endpoints                                                                                   
                                                                                                    
# Load a public survey by slug                                                                     
curl "$BASE/api/v1/public/surveys/nps-q2"                                                          
                                                                                                    
# Resolve a bearer token (use the token returned from link creation)                               
curl -X POST "$BASE/api/v1/public/links/resolve" \                                                 
-H "Content-Type: application/json" \                                                            
-d '{"token": "PASTE_TOKEN_HERE"}'                                                               
                                                                                                    
---                                                                                                
Submissions                                                                                        
                                                                                                
# Create an authenticated submission                                                               
curl -X POST "$BASE/api/v1/projects/1/surveys/1/submissions" \                                     
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "survey_version_id": 1,                                                                        
    "submitted_by_user_id": 2,                                                                     
    "answers": [                                                                                   
    {                                                                                            
        "question_key": "recommend_score",                                                         
        "answer_family": "rating",                                                                 
        "answer_value": {"value": 9}                                                               
    },                                                                                           
    {                                                                                            
        "question_key": "open_feedback",                                                           
        "answer_family": "field",                                                                  
        "answer_value": {"value": "Great product overall."}                                        
    }                                                                                            
    ],                                                                                             
    "started_at": "2026-04-04T10:00:00Z",                                                          
    "submitted_at": "2026-04-04T10:03:00Z"                                                         
}'                                                                                               
                                                                                                    
# Create a public-link submission                                                                  
curl -X POST "$BASE/api/v1/public/submissions" \                                                   
-H "Content-Type: application/json" \                                                            
-d '{                                                                                            
    "public_token": "PASTE_TOKEN_HERE",                                                            
    "survey_version_id": 1,                                                                        
    "is_anonymous": true,                                                                          
    "answers": [                                                                                   
    {                                                                                            
        "question_key": "recommend_score",                                                         
        "answer_family": "rating",                                                                 
        "answer_value": {"value": 7}                                                               
    }                                                                                            
    ],                                                                                             
    "submitted_at": "2026-04-04T11:00:00Z"                                                         
}'                                                                                               
                                                                                                    
# List submissions for a project (with optional filters)                                           
curl "$BASE/api/v1/projects/1/submissions"                                                         
curl "$BASE/api/v1/projects/1/submissions?survey_id=1"                                             
curl "$BASE/api/v1/projects/1/submissions?status=stored"                                           
curl "$BASE/api/v1/projects/1/submissions?submission_channel=authenticated"                        
                                                                                                    
# Get one linked submission with answers and resolved identity                                     
curl "$BASE/api/v1/projects/1/submissions/1?include_answers=true&resolve_identity=true"            
                                                                                                    
# Get without answers (just the registry record)                                                   
curl "$BASE/api/v1/projects/1/submissions/1"                                                       
                                                                                                    
---                                                       