# Survey JSON Shapes Examples  v1

## Families

#### Choice

```json
{
  "id": "q6",
  "title": "Favourite Colour",
  "label": "What is your favourite colour?",
  "family": "choice",
  "choice": {
    "schema": {
      "options": [
        { "id": "a1", "label": "Red" },
        { "id": "a2", "label": "Blue" }
      ],
      "min_selected": 1,
      "max_selected": 1
    },
    "ui": {
    }
  }
}
```

```json
{
  "id": "q5",
  "title": "Hobbies",
  "label": "Select your hobbies",
  "family": "choice",
  "choice": {
    "schema": {
      "options": [
        { "id": "A", "label": "Reading" },
        { "id": "B", "label": "Traveling" },
        { "id": "C", "label": "Cooking" }
      ],
      "min_selected": 1,
      "max_selected": 3
    },
    "ui": {
    }
  }
}
```

#### Field

```json
{
  "id": "q4",
  "title": "Contact Information",
  "label": "What is your email address?",
  "family": "field",
  "field": {
    "schema": {
      "field_type": "email"
    },
    "ui": {
      "placeholder": "name@example.com"
    }
  }
}
```

```json
{
  "id": "q3",
  "title": "Personal Information",
  "label": "Enter your age",
  "family": "field",
    "field": {
    "schema": {
      "field_type": "number"
    },
    "ui": {
      "placeholder": "e.g. 30"
    }
  }
}
```

##### Allowed field types

`field_type`'s: "short_text", "long_text", "email", "number", "date", "phone"

#### Matching

```json
{
  "id": "q2",
  "title": "Geography Quiz",
  "label": "Match each country to its capital city",
  "family": "matching",
  "matching": {
    "schema": {
      "prompts": [
        { "id": "p_A", "label": "Australia" },
        { "id": "p_B", "label": "France" }
      ],
      "matches": [
        { "id": "m_A", "label": "Canberra" },
        { "id": "m_B", "label": "Paris" },
        { "id": "m_C", "label": "Madrid" }
      ]
    },
    "ui": {
    }
  }
}
```

#### Rating

```json
{
  "id": "q1",
  "title": "Satisfaction Survey",
  "label": "How satisfied are you?",
  "family": "rating",
    "rating": {
    "style": "slider",
    "schema": {
      "range": { 
        "min": -5,
        "max": 5,
        "step": 1
      },
    },
    "ui": {
      "left_label": "Not satisfied",
      "right_label": "Very satisfied",

      "step": 1
    }
  }
}
```

```json
{
  "label": "Rate the following aspects of our service",
  "family": "rating",
  "rating": {
    "style": "emoji",
    "schema": {
      "emoji_list": "sad_to_happy",
      "words": true
    },
    "ui": {
      "left_label": "Poor",
      "right_label": "Excellent"
    }
  }
}
```

```json
{
  "label": "How likely are you to recommend our product?",
  "family": "rating",
  "rating": {
    "style": "star",
    "schema": {
      "stars": 5
    },
    "ui": {
      "left_label": "Not likely",
      "right_label": "Very likely"
    }
  }
}
```

#### UI style's for ratings can only be these options

##### emoji

```code
    "emoji_list": "sad_to_happy"/"angry_to_happy"/"disgust_to_happy"
    "words": true/false
```

##### slider

```code
    "step": 1/2/3/4/5 etc.
```

##### star

```code
    No additional options.
```



```json
{
  "type": "question",
  "sort_key": 100000, 
  "content": {
    "id": "q1",
    "title": "Satisfaction Survey",
    "label": "How satisfied are you?",
    "family": "rating",
    "definition": {
      "variant": "slider",
      "range": {
        "min": -5,
        "max": 5,
        "step": 1
      },
      "ui": {
        "left_label": "Not satisfied",
        "right_label": "Very satisfied"
      }
    }
  }
}
```

```json
{
  "type": "question",
  "sort_key": 150000, 
  "content": {
    "id": "q15",
    "title": "Satisfaction Survey",
    "label": "Out of five stars, what do you rate this?",
    "family": "rating",
    "definition": {
      "variant": "stars",
      "stars": 5,
      "ui": {
        "left_label": "Not satisfied",
        "right_label": "Very satisfied"
      }
    }
  }
}
```

```json
{
  "type": "question",
  "sort_key": 125000, 
  "content": {
    "id": "q16",
    "title": "Satisfaction Survey",
    "label": "How would you rate our service using emojis?",
    "family": "rating",
    "definition": {
      "variant": "emoji",
      "emoji_list": "sad_to_happy",
      "words": true,
      "ui": {
        "left_label": "Not satisfied",
        "right_label": "Very satisfied"
      }
    }
  }
}
```

```json
{
  "type": "question",
  "sort_key": 200000, 
  "content": {
    "id": "q2",
    "title": "Geography Quiz",
    "label": "Match each country to its capital city",
    "family": "matching",
    "definition": {
      "prompts": [
        { "id": "p_A", "label": "Australia" },
        { "id": "p_B", "label": "France" }
      ],
      "matches": [
        { "id": "m_A", "label": "Canberra" },
        { "id": "m_B", "label": "Paris" },
        { "id": "m_C", "label": "Madrid" }
      ]
    }
  }
}
```
```json
{
  "type": "question",
  "sort_key": 300000, 
  "content": {
    "id": "q3",
    "title": "Personal Information",
    "label": "Enter your age",
    "family": "field",
    "definition": {
      "field_type": "number",
      "ui": {
        "placeholder": "e.g. 30"
      }
    }
  }
}
```
```json
{
  "type": "question",
  "sort_key": 400000, 
  "content": {
    "id": "q4",
    "title": "Favorite Color",
    "label": "What's your favorite color?",
    "family": "choice",
    "definition": {
      "min": 1,
      "max": 1,
      "options": [
        { "id": "a", "label": "Red" },
        { "id": "b", "label": "Blue" },
        { "id": "c", "label": "Green" },
        { "id": "d", "label": "Yellow" },
        { "id": "e", "label": "Orange" },
        { "id": "f", "label": "Purple" },
        { "id": "g", "label": "Pink" }
      ]
    }
  }
}
```

```json
{
  "type": "question",
  "sort_key": 500000, 
  "content": {
    "id": "q5",
    "title": "Personal Information",
    "label": "When did you start working here? ",
    "family": "field",
    "definition": {
      "field_type": "date",
      "ui": {
      }
    }
  }
}
```

```json
{
  "type": "rule",
  "sort_key": 500000,
  "content": {
    "id": "r1",
    "if": {
      "match": "ALL",//"ANY"/"NONE" 
      "conditions": [
        {
          "target_id": "q4",// "family": "choice"
          "family": "choice",
          "requirements": {
            "required": ["a"],
            "forbidden": ["b"],
            "any_of": ["d", "e"]
          }
        },
        {
          "target_id": "q2", // "family": "matching"
          "family": "matching",
          "requirements": {
            "required": [{"p_A": "m_A"},{ "p_B": "m_B"}],
          }
        },
        {
          "target_id": "q1",// "family": "rating"
          "family": "rating",
          "requirements": {
            "min": 3,
            "max": 5
          }
        },
        {
          "target_id": "q3",// "family": "field"
          "family": "field",
          "requirements": {
            "type": "number",
            "operator": "GTE",//"LT"/"LTE"/"GT"/"GTE"/"EQ"/"NEQ"
            "value": 18
          }
        },
        {
          "target_id": "q5",// "family": "field"
          "family": "field",
          "requirements": {
            "type": "date",
            "operator": "before",//"before"/"after"
            "value": "2023-01-01"
          }
        }
      ]

      
    },
    "then": {
      "set": [//set/do
      {
        "target_id": "q6",
        "visible": true,
        "required": true
      },
      {
        "target_id": "q7",
        "visible": true,
        "required": true
      },
      {
        "target_id": "q8",
        "visible": false,
      },
      {
        "target_id": "q9",
        "required": false
      }
      ]
    },
    "else": {
      "do": {
        "skip_to": "q10" // "skip_to" / "end_and_submit" / "end_and_discard"
      }
    }
  }
