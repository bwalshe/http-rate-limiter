# ASGI HTTP Rate Limiter

This is a HTTP Rate Limiter based on the system described in chapter 4 of
[_System Design Interview, Vol 1_ by Alex Xu](https://openlibrary.org/books/OL30260884M/System_Design_Interview_-_an_Insider's_Guide_Second_Edition). I created this repo while
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
review. **This write-up is still a work in progress, with a bit of an abrupt
end right now**, but the planned layout is to start by describing the basic
idea of what a rate-limiter is and the broad details of how I have addressed
the problem. Then I will go into some details about the details of the code
and the project setup.

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

### Rate Limit Algorithms
In the book they give an overview of five different algorithms for rate
limiting these are:
   * Token bucket
   * Leaking bucket
   * Fixed window counter
   * Sliding window log
   * Sliding window counter

I am going to focus on the Token Bucket algorithm. With this algorithm,
each client is assigned a bucket which has a fixed capacity `c`. As time
progresses, a token is added to their bucket at a fixed rate of one token
every `r` seconds. Each time a client wants to make a request to our service,
they need to spend a token from their bucket. If there are no tokens left
then they will be blocked and will have to wait at least `r` seconds for a
token to be added to their bucket before they can make another request.

Depending on the choice of `c` and `r`, you can control how consistent
the traffic from individual clients is. If `c` and `r` are both low, then
clients will be restricted to making requests at a fairly constant rate.
On the other hand if `c` and `r` are high, then clients could make occasional
bursts of intense activity by waiting for their bucket to fill and then
expending all their credits at once.


If you want details of the others algorithms then you should get the book.
The key thing though is that not only are there configuration options
for the algorithm are multiple choices for which kind of algorithm to use
and it would be good to keep our options open to use one of these other
algorithms in the future.

Another thing to keep in mind is that these algorithms all depend on measuring
time between requests in some way, and this is something we will need to be
careful about during implementation and testing.

### Requirements
  * Can handle tracking in the order of 100k clients
  * Must not add significant overhead to response time
  * Should be very resistant to denial of service attack
  * Clients should receive a clear message when they go over their limit, i.e
    A HTTP 429 response.
  * It should be possible to configure the algorithm being used to perform the
    rate limiting.

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
    else:
        await send(LimitRateError())
```

Here, the magic `is_within_limit(scipe:dict) -> bool` first checks the `scope`
object to determine who the client is, and then checks if this particular
client is still under their limit. If the client is under their limit, then the
app is proxied. If not then `send(...)` function is used to send an error message
back to the client.

I like this solution because it is conceptually very simple, but when combined
with an ASGI compatible server like [Uvicorn](https://www.uvicorn.org/), it
should scale up well to the number of users that we are expecting. The two main
issues we will face are that first, the `is_within_limit(...)` function must
return quickly, as this would block the event loop, and secondly we will need
to be careful about how much memory we use as the ASGI app could be running in
the same process as the app it is protecting.

### Python Class Structure
This problem lends itself well to object composition. The fundamental business
logic of inspecting the request, deciding if the client has exceeded their rate
and then either forwarding their request or sending an HTTP 429 response is
implemented in the `RateLimiter` class, but the specifics on _how_ to identify
the client and then determine if this specific client is above their limit are
delegated to two `Callable` objects, `key_fn` and `algorithm`, that are passed
to the `RateLimiter` at initialisation time.

These `Callable`s are then used at request time as follows:

```Python
if scope["type"] == "http":
    key = self._key_fn(scope)
    if not self._algorithm(key, datetime.now()):
        self._logger.info("Request blocked for exceding rate limit.")
        await self._limit_response(scope, receive, send)
        return
await self._app(scope, receive, send)
```

First we check this is actually a HTTP request. Then `key_fn` is used to
taking the `scope` object and producing a byte string that uniquely identifies
the client making the request, before passing this to the `algorithm` callable
which actually makes the decision on whether to let the client through or not.

One important thing which might be easy to overlook is that any time a request
is blocked, this is logged explicitly. This might seem like a trivial thing,
but ff you are in a production environment and your users' legitimate requests
are being blocked from accessing your service, you will be really glad of
having nice clear indicators that allow you to either identify or rule out this
particular component being the cause of the problem.
