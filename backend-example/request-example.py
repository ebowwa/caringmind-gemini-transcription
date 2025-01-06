"""
Install an additional SDK for JSON schema support Google AI Python SDK

$ pip install google.ai.generativelanguage
"""

import os
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  return file

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_schema": content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["full_audio_transcribed", "conversation_analysis"],
    properties = {
      "full_audio_transcribed": content.Schema(
        type = content.Type.BOOLEAN,
        description = "Indicates if the entire audio file has been transcribed.",
      ),
      "conversation_analysis": content.Schema(
        type = content.Type.ARRAY,
        description = "List of analyzed turns in the conversation. Each entry corresponds to one speaker's turn.",
        items = content.Schema(
          type = content.Type.OBJECT,
          enum = [],
          required = ["diarization_html", "transcription_html", "timestamps_html", "tone_analysis", "confidence", "summary"],
          properties = {
            "diarization_html": content.Schema(
              type = content.Type.STRING,
              description = "HTML structure indicating the speaker label. E.g., <h1>Speaker 1</h1>",
            ),
            "transcription_html": content.Schema(
              type = content.Type.STRING,
              description = "HTML structure for the verbatim transcription. E.g., <p>Hello everyone, ...</p>",
            ),
            "timestamps_html": content.Schema(
              type = content.Type.STRING,
              description = "HTML structure indicating approximate time range. E.g., <h2>0:00 - 0:15</h2>",
            ),
            "emotional_prosody_html": content.Schema(
              type = content.Type.STRING,
              description = "HTML structure describing emotional cues, if any. E.g., <ul><li>Rising pitch</li></ul>",
            ),
            "intent_html": content.Schema(
              type = content.Type.STRING,
              description = "HTML structure indicating predicted intent, if relevant. E.g., <strong>Requesting information</strong>",
            ),
            "tone_analysis": content.Schema(
              type = content.Type.OBJECT,
              description = "Analysis of the speaker's tone, including the dominant tone and supporting indicators.",
              enum = [],
              required = ["tone", "indicators"],
              properties = {
                "tone": content.Schema(
                  type = content.Type.STRING,
                  description = "The dominant tone identified (e.g., 'confident', 'defensive').",
                ),
                "indicators": content.Schema(
                  type = content.Type.ARRAY,
                  description = "Supporting details for the identified tone, such as 'clear explanations' or 'hesitant tone.'",
                  items = content.Schema(
                    type = content.Type.STRING,
                    description = "A specific indicator of the tone.",
                  ),
                ),
              },
            ),
            "confidence": content.Schema(
              type = content.Type.NUMBER,
              description = "Confidence score for the tone detection (0 to 100).",
            ),
            "red_flags": content.Schema(
              type = content.Type.ARRAY,
              description = "List of potential red flags detected during the turn, if any.",
              items = content.Schema(
                type = content.Type.OBJECT,
                enum = [],
                required = ["description", "evidence"],
                properties = {
                  "description": content.Schema(
                    type = content.Type.STRING,
                    description = "Description of the red flag (e.g., 'Potential deception detected').",
                  ),
                  "evidence": content.Schema(
                    type = content.Type.ARRAY,
                    description = "Supporting evidence for the red flag, such as 'inconsistent phrasing' or 'elevated pitch.'",
                    items = content.Schema(
                      type = content.Type.STRING,
                      description = "A specific piece of evidence supporting the red flag.",
                    ),
                  ),
                },
              ),
            ),
            "summary": content.Schema(
              type = content.Type.STRING,
              description = "Concise summary of the speaker's contribution to the conversation.",
            ),
          },
        ),
      ),
    },
  ),
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

# TODO Make these files available on the local file system
# You may need to update the file paths
files = [
  upload_to_gemini("Recorded Audio November 03, 2024 - 9:22PM.ogg", mime_type="audio/ogg"),
]

chat_session = model.start_chat(
  history=[
    {
      "role": "user",
      "parts": [
        files[0],
        "Analyze the provided audio conversation between multiple participants. For each speaker, extract and render in HTML the following (where applicable):\n\nDiarization: Which speaker is talking, using <h1> tags for speaker labels.\nTranscription: The verbatim text in <p> tags.\nTimestamps: The approximate time range (e.g., 0:00-0:15) in a suitable heading or paragraph tag (e.g., <h2> or <p>).\nEmotional Prosody: Indicators of emotional state in <p> or <ul> tags.\nTone Analysis: Include dominant tone and supporting indicators if sufficient evidence exists.\nRed Flags: Possible deception or tension signs, if clearly present.\nConfidence: A 0–100% rating of confidence in the tone detection.\nIntent Prediction (optional): If there is enough context to suggest a likely intent, enclose it in an HTML tag of your choice (e.g., <em> or <strong>).\nSummary: A concise summary of the speaker’s contribution.\nImportant: Only include red flags or emotional prosody if there is clear evidence. Do not invent details not present in the audio. If no conversation is detected, return an empty array for conversation_analysis.\n\nFinally, your output must be a valid JSON object following the schema below. Make sure to include:\n\nA top-level boolean field covers_full_audio indicating whether the entire audio was fully transcribed.\nAn array conversation_analysis that contains one entry per speaker turn with the necessary HTML-structured fields.\n\nThe goal is to handle the full audio files, and accurately",
      ],
    },
    {
      "role": "model",
      "parts": [
        "```json\n",
        "{\"conversation_analysis\": [{\"confidence\": 85, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 discusses the five different states of the human brain, focusing on beta and theta states in relation to hypnosis.  They explain that the theta state is ideal for hypnosis due to the thin filter between the conscious and subconscious mind, making the person more receptive to suggestions.\", \"timestamps_html\": \"<h2>0:00-1:00</h2>\", \"tone_analysis\": {\"indicators\": [\"clear explanations\", \"confident tone\"], \"tone\": \"informative\"}, \"transcription_html\": \"<p>Okay. Human brain has five different states; alpha, beta, delta, theta, and gamma. The most important for the context of like contextualizing hypnosis have to do with beta and theta. Beta is most of a human being's waking state. And in a beta state, the filter between the conscious and the subconscious mind is the thickest, okay? Theta is a state right before delta, delta being deep sleep. So theta, right after you as soon as you wake up, right before you go to bed. Um this state is also called hypnagogia. Hypnagogia, it's literally theta, like it's another term for theta, which is where the term hypnosis comes from. But the reason why um that state is so important is because, when your brain is in this state the filter between your conscious and subconscious mind is the thinnest. And so you are most receptive to suggestions, aka this is the state that you have to be in in order to</p>\"}, {\"confidence\": 90, \"diarization_html\": \"<h1>Speaker 2</h1>\", \"summary\": \"Speaker 2 asks clarifying questions about the theta state and how to achieve it, showing curiosity and engagement.\", \"timestamps_html\": \"<h2>1:00-1:30</h2>\", \"tone_analysis\": {\"indicators\": [\"curious questions\", \"engaged tone\"], \"tone\": \"inquiring\"}, \"transcription_html\": \"<p>Okay. This is like how this is the state that a brain So how do you get to this state? I'm sorry to cut you off. No, it's cool, it's cool. How do you get to this state?</p>\"}, {\"confidence\": 88, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 describes how to induce the theta state in a one-on-one hypnosis session, emphasizing the importance of the client's willingness and trust, comparing it to a shamanic experience.\", \"timestamps_html\": \"<h2>1:30-2:30</h2>\", \"tone_analysis\": {\"indicators\": [\"descriptive language\", \"calm tone\", \"metaphorical comparison\"], \"tone\": \"explaining\"}, \"transcription_html\": \"<p>Um in the world of hypnosis if you're working with a one-on-one client, you get into the state by a method of induction. So but it's also suggestion, so it's like the person that I work with has to want to. You know, from my perspective it's very much like a shamanic experience, where it's like we're diving into your subconscious but like you're trusting me with the like to lead the ship, like it's your ship, like your water, but like</p>\"}, {\"confidence\": 85, \"diarization_html\": \"<h1>Speaker 2</h1>\", \"summary\": \"Speaker 2 seeks to understand how the client reaches the theta state, focusing on their role in the process.\", \"timestamps_html\": \"<h2>2:30-3:00</h2>\", \"tone_analysis\": {\"indicators\": [\"clarifying questions\", \"interested tone\"], \"tone\": \"inquiring\"}, \"transcription_html\": \"<p>So like you're just being guided through. How does the user or the person that you how do they like get into the state to allow someone to Are you in the context of are you talking about the context of this this audio file or you talking about the concept</p>\"}, {\"confidence\": 92, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 explains that the process involves framing, giving an example of how a suggestion like \\\"sleep\\\" can induce relaxation and guide the client into a theta state. They also emphasize compliance with suggestions.\", \"timestamps_html\": \"<h2>3:00-4:00</h2>\", \"tone_analysis\": {\"indicators\": [\"provides an example\", \"calm explanation\"], \"tone\": \"instructive\"}, \"transcription_html\": \"<p>Context of you with a person. Yeah, well by framing it. So when I say sleep, you close your eyes and relax your body. Okay, so I have to frame myself I have like prompt myself. You have to be like yeah, you have to be compliant with it, the suggestion. And then And then I just kind of stay here and then eventually it just works. No. Well, yes and no. If you if you actually wanted to experience a session, I would not I would not be opposed, but not not tonight.</p>\"}, {\"confidence\": 80, \"diarization_html\": \"<h1>Speaker 2</h1>\", \"summary\": \"Speaker 2 expresses hesitation and uncertainty but ultimately agrees to a later session.\", \"timestamps_html\": \"<h2>4:00-4:30</h2>\", \"tone_analysis\": {\"indicators\": [\"hesitant agreement\", \"slightly nervous tone\"], \"tone\": \"hesitant\"}, \"transcription_html\": \"<p>Yeah, yeah, I'm okay. I I don't know. I've never done it before. Not to say I'm nervous.</p>\"}, {\"confidence\": 95, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 points out that the listener has already experienced a trance-like state, illustrating with a question that caused a brief moment of trance.  They discuss different levels of trance, including recall, hallucination, and vivid imagery, relating it to storytelling and hypnosis.\", \"timestamps_html\": \"<h2>4:30-5:30</h2>\", \"tone_analysis\": {\"indicators\": [\"illustrative example\", \"calm explanation\"], \"tone\": \"explaining\"}, \"transcription_html\": \"<p>No, you've done it you've done it you've you've Well, you've done it in a way because Okay, let me ask you a question. When how many windows are in your bedroom? Who? You just went into trance right there. I see. So that's considered a trance. Yeah. They're different stages. Yeah, recall, hallucination, vivid imagery that storytellers are hypnotists. But it's like a human prompter.</p>\"}, {\"confidence\": 82, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 continues explaining that there are deeper levels of trance, using examples like psychedelic concerts to illustrate the concept of trance.\", \"timestamps_html\": \"<h2>5:30-6:30</h2>\", \"tone_analysis\": {\"indicators\": [\"illustrative examples\", \"comparisons\"], \"tone\": \"explaining\"}, \"transcription_html\": \"<p>Yeah. But the thing is is that like think about someone who's like I don't know, high on drugs at a uh shaky graves concert or some shit. Like all right, some other psychedelic concert, psychedelic Tim and Paula Rufus, the Soul whatever. Like they're in fucking trance bro. They're tranced out. Um But let's think about it like this. So it's not really like it's something like spooky spooky. It's more like you're very calm and then you know, it's just like reinforcing it. Yeah. I see. Granted it's a it's a it's a powerful tool. Powerful tool because it's always like it's always a knife. You can perform surgery with a knife, you can kill someone with a knife. Yeah. So it's like it it is powerful, like it's the closest thing to magic that I've that the last seminar I went to bro like dude had a stutter. Put him to sleep. Like stutter's gone like soon as he woke up.</p>\"}, {\"confidence\": 88, \"diarization_html\": \"<h1>Speaker 2</h1>\", \"summary\": \"Speaker 2 asks if the person needs to be asleep to enter a trance state.\", \"timestamps_html\": \"<h2>6:30-7:00</h2>\", \"tone_analysis\": {\"indicators\": [\"clarifying question\", \"curious tone\"], \"tone\": \"inquiring\"}, \"transcription_html\": \"<p>And they have to be like asleep? No.</p>\"}, {\"confidence\": 90, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 explains that the subconscious mind associates words like 'sleep' with relaxation, facilitating entry into a trance. They discuss the concept of relaxation as a path to the theta state.\", \"timestamps_html\": \"<h2>7:00-7:45</h2>\", \"tone_analysis\": {\"indicators\": [\"logical explanations\", \"clear articulation\"], \"tone\": \"explanatory\"}, \"transcription_html\": \"<p>You say sleep, okay, good. The subconscious mind has associations. Right? So when I say sleep, your body knows what sleep is, right? You know what sleep is, you know. And so it's like it's the closest thing to getting you into that to getting you into this if I say relax, then it's like you're more inclined to like Can does the user speak when in this state or not?</p>\"}, {\"confidence\": 92, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 confirms that a person can speak while in a trance, highlighting the therapeutic potential of this state for exploring the subconscious mind.\", \"timestamps_html\": \"<h2>7:45-8:30</h2>\", \"tone_analysis\": {\"indicators\": [\"confident assertion\", \"enthusiastic tone\"], \"tone\": \"affirmative\"}, \"transcription_html\": \"<p>You can yeah I mean you can be in like you can be in trance and speak 100%. Yeah, so you can like bro like psychotherapy, you can like This is cool. You can explore the depths of your subconscious mind. I see. You know. Yeah. But even uh even still you can also like fix shit that you don't even know is there without even without even having to learn what it is. But like for example like if someone had trauma like I would be able to help them with that without them having to unpack it and without me having to even know what that was. Because um just and then you can you can I'll say be it's because what ends up happening is that like this is the way that I like to think of it.</p>\"}, {\"confidence\": 87, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 describes how changing brain states to theta allows access to the subconscious mind and its stored memories and emotions. They explain how to use vivid imagery and storytelling to materialize metaphors representing abstract psychological phenomena like fear, love, trauma, etc., and manipulate them for therapeutic purposes.\", \"timestamps_html\": \"<h2>8:30-10:00</h2>\", \"tone_analysis\": {\"indicators\": [\"detailed explanation\", \"logical flow\"], \"tone\": \"instructive\"}, \"transcription_html\": \"<p>When you change the brain state, you're operating in theta which is like and you have better access to subconscious where which is where memories and emotions are forged and stored. Okay? So you have abstract psychological phenomena, like fear, love, pain, trauma, etcetera, disgust. These are like abstract. But what you can do is you can use vivid vivid imagery and storytelling to materialize metaphors. So like you're in this state and we say, okay, cool, your anxiety. I can one ask you what it looks like and now and now like you you start describing a psychic shape of this thing. Or you know I can assume that your anxiety is represented by a dense black like hard cube. And now we can spend the next 15 minutes fucking destroying it, you know? And and because like like we have taken some abstract thing and literally wait it's it's yeah abstracted it onto a metaphor. Now we manipulate that block of data and it will actually like re it's like in the same way that you do the same shit with an LLM, like your brain's will do the same shit, you know? Like you don't have to be super super specific it's kind of like bro like you you know what sleep is you know what sit down is, you know what happens when you destroy a big black cube that represents anxiety. But if you were to do that in a beta state, it's just not going to it's just not going to stick. It's not going to work. Because like you're not you're not in the right brain state.</p>\"}, {\"confidence\": 78, \"diarization_html\": \"<h1>Speaker 2</h1>\", \"summary\": \"Speaker 2 suggests using nighttime deep breaths with real-time EEG as a method.\", \"timestamps_html\": \"<h2>10:00-10:30</h2>\", \"tone_analysis\": {\"indicators\": [\"suggestive tone\", \"calm tone\"], \"tone\": \"suggestive\"}, \"transcription_html\": \"<p>Nighttime deep breaths with uh real-time EEG.</p>\"}, {\"confidence\": 85, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 responds positively to the suggestion, acknowledging the effectiveness of the method and expressing enthusiasm about the topic.\", \"timestamps_html\": \"<h2>10:30-11:00</h2>\", \"tone_analysis\": {\"indicators\": [\"positive feedback\", \"enthusiastic tone\"], \"tone\": \"enthusiastic\"}, \"transcription_html\": \"<p>Damn bro. Yeah, so that's that's some gas right there. That'll be uh 2500. That's pretty that's pretty interesting. I could I could go on for more bro. This shit is fascinating. I can listen forever, you know. This is pretty cool.</p>\"}, {\"confidence\": 75, \"diarization_html\": \"<h1>Speaker 1</h1>\", \"summary\": \"Speaker 1 concludes the conversation, suggesting they can continue later and asks for feedback on what was discussed.\", \"timestamps_html\": \"<h2>11:00-11:30</h2>\", \"tone_analysis\": {\"indicators\": [\"concluding remarks\", \"calm tone\"], \"tone\": \"concluding\"}, \"transcription_html\": \"<p>So anyways, but well we can call it there. Lots to take from that. Yeah, well I guess let me know what the shit says. Yeah, you wanna see? Yeah. There's many things we can ask here right. But</p>\"}, {\"confidence\": 0, \"diarization_html\": \"<h1>Speaker 3</h1>\", \"summary\": \"No conversation detected.\", \"timestamps_html\": \"<h2>11:30-11:40</h2>\", \"tone_analysis\": {\"indicators\": [], \"tone\": \"no conversation\"}, \"transcription_html\": \"<p></p>\"}], \"full_audio_transcribed\": true}",
        "\n```",
      ],
    },
  ]
)

response = chat_session.send_message("INSERT_INPUT_HERE")

print(response.text)