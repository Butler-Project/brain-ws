# Voice Architecture Report

## Overview

This document describes the voice-processing architecture shown in the latest system diagram.

The design captures raw microphone audio, detects when a human speaking segment is complete, transcribes that segment into text, sends the text to the frontend client, generates synthesized speech from the response, and finally publishes the generated audio for playback.

## High-Level Flow

```text
Audio In Node
  -> /RawAudioIn
  -> Speech Turn Segmenter Node
  -> ASR Node
  -> FrontEnd Client
  -> TTS Node
  -> /RawAudioOut
  -> Audio Out Node
```

## Architecture Table

| Logical Area | Node / Service | Type | Main Communication | Main Input | Main Output | Has State Machine? |
| --- | --- | --- | --- | --- | --- | --- |
| Audio input | `Audio In Node` | ROS2 publisher node | Publishes audio chunks to `/RawAudioIn` | Microphone stream | Raw audio chunks | No |
| Raw audio transport | `/RawAudioIn` | ROS2 topic | Connects `Audio In Node` to `Speech Turn Segmenter Node` | Audio chunks | Audio chunks | No |
| Speech turn detection | `Speech Turn Segmenter Node` | ROS2 processing node | Subscribes to `/RawAudioIn`, uses `VAD Service Docker`, sends full segment to `ASR Node` | Raw audio chunks | Complete voice segment | Yes |
| Voice activity detection | `VAD Service Docker (silero)` | Docker service | Connected to `Speech Turn Segmenter Node` | Audio chunk or frame data | Human voice pause detection | No |
| Speech recognition | `ASR Node` | ROS2 action-oriented processing node | Receives a full segment from `Speech Turn Segmenter Node`, uses `Parakeet Service Docker`, sends text to `FrontEnd Client` | Whole voice segment | Transcript text | Yes |
| ASR backend | `Parakeet Service Docker` | Docker service | Connected to `ASR Node` | Voice segment | Transcribed text | No |
| Frontend orchestration | `FrontEnd Client` | ROS2 client node | Receives text from `ASR Node`, sends text to `TTS Node` | Transcript text | Assistant text request for TTS | No |
| Speech synthesis | `TTS Node` | ROS2 processing node | Receives text from `FrontEnd Client`, uses `GLaDOS + phonemizer` service, publishes to `/RawAudioOut` | Response text | Synthesized audio chunks | No |
| TTS backend | `GLaDOS + phonemizer Docker Service` | Docker service | Connected to `TTS Node` | Text | Synthesized speech audio | No |
| Raw output audio transport | `/RawAudioOut` | ROS2 topic | Connects `TTS Node` to `Audio Out Node` | Synthesized audio chunks | Synthesized audio chunks | No |
| Audio output | `Audio Out Node` | ROS2 subscriber node | Subscribes to `/RawAudioOut` | Synthesized audio chunks | Speaker playback | No |

## Component Description

### Audio In Node

`Audio In Node` captures live audio from the microphone and publishes audio chunks into the `/RawAudioIn` topic.

### Speech Turn Segmenter Node

`Speech Turn Segmenter Node` subscribes to `/RawAudioIn` and analyzes the incoming stream to detect when a human voice pause indicates that a complete speech segment is ready.

This node relies on `VAD Service Docker (silero)` to detect human voice pauses. Once a complete segment is identified, it sends the whole voice segment for processing to the `ASR Node`.

### ASR Node

`ASR Node` receives the full voice segment and forwards it to `Parakeet Service Docker` to transcribe audio into text.

After transcription is completed, the node sends the recognized text to the `FrontEnd Client`.

### FrontEnd Client

`FrontEnd Client` receives text from the `ASR Node`. Based on the diagram, this component acts as the next consumer of the transcript and forwards text to the `TTS Node`.

### TTS Node

`TTS Node` receives text from the `FrontEnd Client` and uses `GLaDOS + phonemizer Docker Service` to synthesize speech audio.

It then publishes the generated audio into `/RawAudioOut`.

### Audio Out Node

`Audio Out Node` subscribes to `/RawAudioOut` and plays the synthesized speech audio.

## State Machines

The latest diagram shows exactly two state machines.

### Speech Turn Segmenter Node State Machine

States shown in the diagram:

- `ERROR`
- `SPEECH-INGEST`
- `EMIT-MESSAGE`

Interpretation:

- `ERROR`: the node is in a failure condition
- `SPEECH-INGEST`: the node is consuming and analyzing incoming audio
- `EMIT-MESSAGE`: the node has detected a complete speech segment and emits it for downstream processing

### ASR Node State Machine

States shown in the diagram:

- `ERROR`
- `INIT`
- `READY`
- `TRANSCRIBING`

Interpretation:

- `ERROR`: the ASR node is in a failure condition
- `INIT`: the ASR node is initializing resources or backend connectivity
- `READY`: the ASR node is ready to accept a voice segment
- `TRANSCRIBING`: the ASR node is actively converting audio to text

## End-to-End Sequence

1. `Audio In Node` publishes audio chunks to `/RawAudioIn`.
2. `Speech Turn Segmenter Node` subscribes to `/RawAudioIn`.
3. `Speech Turn Segmenter Node` uses `VAD Service Docker (silero)` to detect a human voice pause.
4. When a complete segment is ready, `Speech Turn Segmenter Node` sends the whole voice segment to `ASR Node`.
5. `ASR Node` sends the segment to `Parakeet Service Docker`.
6. `Parakeet Service Docker` returns the transcription result.
7. `ASR Node` sends the text to `FrontEnd Client`.
8. `FrontEnd Client` sends text to `TTS Node`.
9. `TTS Node` uses `GLaDOS + phonemizer Docker Service` to synthesize speech.
10. `TTS Node` publishes synthesized audio to `/RawAudioOut`.
11. `Audio Out Node` subscribes to `/RawAudioOut` and plays the audio.

## Summary

The architecture in the latest diagram is composed of three main processing stages:

- speech turn segmentation
- speech-to-text transcription
- text-to-speech synthesis

The diagram explicitly defines only two state machines:

- `Speech Turn Segmenter Node`
- `ASR Node`

All other components are represented as communication, backend, or transport blocks without an explicit internal state machine.
