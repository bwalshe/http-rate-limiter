# ASGI HTTP Rate Limiter

This is a HTTP Rate Limiter based on the system described in chapter 4 of
_System Design Interview, Vol 1_ by Alex Xu. I created this repo while
preparing for an coding interview, so that I could have a few concepts
fresh in my mind.

This is not intended as a production-ready
rate-limiter, and it never will be. If you want one of those, then you
could look at [this](https://github.com/abersheeran/asgi-ratelimit). I
Haven't used it myself, but it is currently recommended by the
[Starlette](https://github.com/encode/starlette) project, so it's worth
checking out.

Another caveat is that is that while this is based off something out
of a system design book, I created this while preparing for a coding
interview, and so I was more concerned with preparing for that than
I was with designing a good overall system. Specifically the things I
wanted to practice were:

 * Test driven development (because the job listing said this was important to
   them)
 * Async functions (Just because I was a bit out of practice on them)
 * Setting up the project, including tooling like a linter, as this
   had come up during my screening call and I felt my answers here could
   have been better.

With all that said, let's look at what I did and try to give it a bit of a
review. I'll start by describing the basic idea of what a rate-limiter is and
the broad details of how I have addressed the problem. Then I will say a bit
about the project setup, before going into some details of the code.

## Rate Limiting
Rate limiting is a fairly simple concept. If we have a service, we may wish to
put some control in place that prevents clients from accessing too many times
in some given time period. There are a few reasons we would want to do this
  * To prevent "greedy" users from using up all the resources and blocking
    out other clients from making use of the system.
  * To prevent the system becoming overloaded and becoming unstable.
  * To allow us to better plan for the cost of running the system, especially
    if we are using elastic cloud services.

Basically, the idea is to prevent any one client from sending a burst of quick
activity that we aren't ready to deal with. It is intended to prevent anyone
sending in thousands of requests a second when you only budgeted for hundreds
of requests per user

It's not really intended for dealing with the case where customers have some
subscription that allows them to use the service 100 times a month, and we
need to keep track of their usage level and billing details so that they do
not find a way of using our service for free - I would say that is out of
scope. I also would say that if we need to do any authentication to identify
the client before applying the rate limit, that is also out of scope, and
should be taken care of by a dedicated authentication system.

### Requirements
  * Can handle tracking in the order of 100k clients
  * Must not add significant overhead to response time
  * Should be very resistant to denial of service attack
  * Clients should receive a clear message when they go over their limit.
    That is a HTTP 429 response.


## Implementation

Rate limiting is typically implemented server-side, as putting it client
side leaves you open to a malicious client finding some way of overriding
their limit. When implementing things server-side there is a further
consideration - the limiter could be made part of the service that it is
guarding, or it could exist as some form middleware.


I have chosen to implement it as an
[ASGI](https://asgi.readthedocs.io/en/latest/) middleware component. ASGI
is a standard for implementing web apps in Python which use async-aware
web servers. By implementing my limiter using ASGI, I then have the option of
attaching it directly to a Python web app, or using it as part of an API
gateway that proxies out to other services.

The basic structure of an ASGI app is very simple. You just have to
implement a function with the following signature

```Python
async def application(scope, receive, send):
   ...
```

Where:
  * **scope** is a dictionary object containing information about
    the request. For example the HTTP query string, the headers
    information about the client, etc. In a short lived request,
    most of the information will be in this object.
  * **receive** is an awaitable function which allows the app
    to poll for more data from the client in a long lived request
  * **send** another awaitable function which is used to send a
    response back to the client.

Implementing a proxy middleware is very straightforward. If `app` is
a ASGI app, then a proxy could be implemented as follows:

```Python
async def proxy(scope, receive, send):
  app(scope, receive, send)
```

Here, any time `proxy(...)` is called, it just forwards the details to `app`
without touching anything.

The rate-limiter is essentially just a proxy that does a check before deciding
to forward the request, or end the connection and return a 429 to the client. A
very rough implementation might look like this:

```Python
async def rate_limit(scope, receive, send):
  if is_within_limit(scope):
    app(scope, receive, send)
  else await send(LimitRateError())
```

Here, the magic `is_within_limit(scipe:dict) -> bool` first checks the `scope`
object to determine who the client is, and then checks if this particular
client is still under their limit. If the client is under their limit, then the
app is proxied. If not then `send` function is used to send an error message
back to the client.

I like this solution because it is conceptually very simple, but when combined
with an ASGI compatible server like [Uvicorn](https://www.uvicorn.org/), it
should scale up well to the number of users that we are expecting. The two main
issues we will face are that first, the `is_within_limit` function must return
quickly, as this would block the event loop, and secondly we will need to be
careful about how much memory we use as the ASGI app could be running in the
same process as the app it is protecting.
