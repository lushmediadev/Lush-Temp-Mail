# UI System

## Product Language
- LushMail uses a clean mail-workspace style with a white content surface, slate borders/text, and orange `lush-500` actions.
- Admin is a dense inbox workspace. User mode is a simpler lookup-and-read flow.

## Layout Patterns
- Desktop user inbox: search hero, alias summary, message list beside a reading pane.
- Mobile user inbox: compact search hero, message list in normal page flow, full-screen reader overlay after selecting a message.
- Avoid nested scroll regions on mobile unless the region is the active full-screen reader.

## Components
- Primary buttons use solid orange.
- The standalone mail composer opens from an orange toolbar action before search and uses a focused modal with To, CC, subject, and message fields.
- Message rows use simple borders, avatar, sender, subject, preview, and relative time.
- Detail views use sender meta, subject, timestamp, then rendered email body.

## Constraints
- Preserve Vietnamese text as UTF-8.
- Keep border radii and decoration restrained.
- Do not add decorative cards or marketing sections to operational mail screens.
