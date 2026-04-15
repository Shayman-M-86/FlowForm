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
