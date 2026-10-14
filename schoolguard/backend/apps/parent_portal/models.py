# No models of its own -- this app is a read-only view over Parent,
# Student, Invoice, Payment, and Receipt (all owned by students/fees apps).
# The only new thing here is the ACCESS CONTROL: whether the requesting
# user's linked Parent record is actually a parent of the requested
# student, checked in every view below, never assumed from a role alone.
