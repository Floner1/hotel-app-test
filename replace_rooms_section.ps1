# Read the flowing gallery section from about.html
$aboutHtml = Get-Content "site1\templates\about.html" -Encoding UTF8 -Raw

# Extract the flowing gallery section (lines 407-510)
$lines = $aboutHtml -split "`r?`n"
$gallerySection = ($lines[406..509] -join "`n")

# Modify the gallery section for rooms
$roomsGallerySection = $gallerySection -replace 'Photos', 'Rooms &amp; Suites' -replace 'These photos give you a clear look at the hotel before you arrive.*?awaits you\.', 'Our rooms offer a quiet place to rest. Simple layouts, comfortable beds, and a calm setting make it easy to relax. Each room is clean, well kept, and designed for a good night's sleep. Whether you stay one night or longer, you will have everything you need to feel comfortable.'

# Replace in home.html
$homeHtml = Get-Content "site1\templates\home.html" -Encoding UTF8 -Raw

# Find and replace the grid-based rooms section in home.html
$oldSection = @'
    <!-- Rooms and Suites Section -->
    <!-- Showcase of available room types and their pricing -->
    <section class="section">
      <div class="container">
        <!-- Section Header -->
        <div class="row justify-content-center text-center mb-5">
          <div class="col-md-7">
            <h2 class="heading" data-aos="fade-up">Rooms &amp; Suites</h2>
            <p data-aos="fade-up" data-aos-delay="100">Our rooms offer a quiet place to rest. Simple layouts, comfortable beds, and a calm setting make it easy to relax. Each room is clean, well kept, and designed for a good night's sleep. Whether you stay one night or longer, you will have everything you need to feel comfortable.</p>
          </div>
        </div>
        <!-- Room Cards Grid -->
        <div class="row justify-content-center">
          {% for room in room_types %}
          <div class="col-md-6 col-lg-4" data-aos="fade-up">
            <a href="#" class="room">
              <figure class="img-wrap">
                {% if '2 Bed No Window' in room.canonical %}
                  <img src="{% static 'images/double room.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '1 Bed No Window' in room.canonical %}
                  <img src="{% static 'images/single bed.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '1 Bed With Window' in room.canonical %}
                  <img src="{% static 'images/window room.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '1 Bed With Balcony' in room.canonical %}
                  <img src="{% static 'images/balcony.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '2 Bed & Balcony Condotel' in room.canonical or 'Condotel' in room.canonical %}
                  <img src="{% static 'images/condotel.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% else %}
                  <img src="{% static 'images/img_1.jpg' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% endif %}
              </figure>
              <div class="p-3 text-center room-info">
                <h2 style="white-space: nowrap;">{{ room.display }}</h2>
                <span class="text-uppercase letter-spacing-1">₫{{ room.price|floatformat:0|intcomma }} / PER NIGHT</span>
              </div>
            </a>
          </div>
          {% endfor %}
        </div>
      </div>
    </section>
'@

$newSection = @'
    <!-- Rooms and Suites Section -->
    <!-- Showcase of available room types with infinite scrolling gallery -->
    <section class="section slider-section bg-light">
      <div class="container">
        <!-- Gallery Title and Description -->
        <div class="row justify-content-center text-center mb-5">
          <div class="col-md-7">
            <h2 class="heading" data-aos="fade-up" style="font-size: 3.5rem !important;">Rooms &amp; Suites</h2>
            <p data-aos="fade-up" data-aos-delay="100" style="font-size: 1.25rem !important;">Our rooms offer a quiet place to rest. Simple layouts, comfortable beds, and a calm setting make it easy to relax. Each room is clean, well kept, and designed for a good night's sleep. Whether you stay one night or longer, you will have everything you need to feel comfortable.</p>
          </div>
        </div>
      </div>
      
      <!-- Infinite Scrolling Room Gallery -->
      <div class="logo-loop-container" data-aos="fade-up" data-aos-delay="200">
        <div class="logo-loop-track">
          <!-- First set of images -->
          <div class="logo-loop-item">
            <img src="{% static 'images/single bed.png' %}" alt="1 Bed No Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/double room.png' %}" alt="2 Bed No Window Room" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/window room.png' %}" alt="1 Bed With Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/balcony.png' %}" alt="1 Bed With Balcony" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/condotel.png' %}" alt="2 Bed & Balcony Condotel" />
          </div>
          
          <!-- Duplicate set for seamless loop -->
          <div class="logo-loop-item">
            <img src="{% static 'images/single bed.png' %}" alt="1 Bed No Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/double room.png' %}" alt="2 Bed No Window Room" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/window room.png' %}" alt="1 Bed With Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/balcony.png' %}" alt="1 Bed With Balcony" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/condotel.png' %}" alt="2 Bed & Balcony Condotel" />
          </div>
        </div>
      </div>
      
      <style>
        .logo-loop-container {
          width: 100%;
          overflow: hidden;
          position: relative;
          padding: 40px 0;
          background: linear-gradient(to right, rgba(248, 248, 248, 1) 0%, transparent 10%, transparent 90%, rgba(248, 248, 248, 1) 100%);
        }
        
        .logo-loop-track {
          display: flex;
          gap: 60px;
          animation: scroll 22s linear infinite;
          will-change: transform;
        }
        
        .logo-loop-item {
          flex-shrink: 0;
          transition: transform 0.3s ease;
        }
        
        .logo-loop-item:hover {
          transform: scale(1.1);
        }
        
        .logo-loop-item img {
          height: 280px;
          width: auto;
          object-fit: cover;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(calc(-50%));
          }
        }
        
        @media (max-width: 768px) {
          .logo-loop-item img {
            height: 200px;
          }
          
          .logo-loop-track {
            gap: 30px;
          }
        }
      </style>
    </section>
    <!-- END section -->
'@

$homeHtml = $homeHtml -replace [regex]::Escape($oldSection), $newSection
Set-Content -Path "site1\templates\home.html" -Value $homeHtml -Encoding UTF8 -NoNewline
Write-Host "✓ Replaced rooms section in home.html"

# Replace in rooms.html
$roomsHtml = Get-Content "site1\templates\rooms.html" -Encoding UTF8 -Raw

$oldSectionRooms = @'
    <section class="section">
      <div class="container">
        <!-- Section Header -->
        <div class="row justify-content-center text-center mb-5">
          <div class="col-md-7">
            <h2 class="heading" data-aos="fade-up">Rooms &amp; Suites</h2>
            <p data-aos="fade-up" data-aos-delay="100">Our rooms offer a quiet place to rest. Simple layouts, comfortable beds, and a calm setting make it easy to relax. Each room is clean, well kept, and designed for a good night's sleep. Whether you stay one night or longer, you will have everything you need to feel comfortable.</p>
          </div>
        </div>
        
        <!-- Room Cards Grid -->
        <div class="row justify-content-center">
          {% for room in room_types %}
          <div class="col-md-6 col-lg-4" data-aos="fade-up">
            <a href="#" class="room">
              <figure class="img-wrap">
                {% if '2 Bed No Window' in room.canonical %}
                  <img src="{% static 'images/double room.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '1 Bed No Window' in room.canonical %}
                  <img src="{% static 'images/single bed.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '1 Bed With Window' in room.canonical %}
                  <img src="{% static 'images/window room.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '1 Bed With Balcony' in room.canonical %}
                  <img src="{% static 'images/balcony.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% elif '2 Bed & Balcony Condotel' in room.canonical or 'Condotel' in room.canonical %}
                  <img src="{% static 'images/condotel.png' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% else %}
                  <img src="{% static 'images/img_1.jpg' %}" alt="{{ room.display }}" class="img-fluid mb-3">
                {% endif %}
              </figure>
              <div class="p-3 text-center room-info">
                <h2 style="white-space: nowrap;">{{ room.display }}</h2>
                <span class="text-uppercase letter-spacing-1">₫{{ room.price|floatformat:0|intcomma }} / PER NIGHT</span>
              </div>
            </a>
          </div>
          {% endfor %}
        </div>
      </div>
    </section>
'@

$newSectionRooms = @'
    <section class="section slider-section bg-light">
      <div class="container">
        <!-- Gallery Title and Description -->
        <div class="row justify-content-center text-center mb-5">
          <div class="col-md-7">
            <h2 class="heading" data-aos="fade-up" style="font-size: 3.5rem !important;">Rooms &amp; Suites</h2>
            <p data-aos="fade-up" data-aos-delay="100" style="font-size: 1.25rem !important;">Our rooms offer a quiet place to rest. Simple layouts, comfortable beds, and a calm setting make it easy to relax. Each room is clean, well kept, and designed for a good night's sleep. Whether you stay one night or longer, you will have everything you need to feel comfortable.</p>
          </div>
        </div>
      </div>
      
      <!-- Infinite Scrolling Room Gallery -->
      <div class="logo-loop-container" data-aos="fade-up" data-aos-delay="200">
        <div class="logo-loop-track">
          <!-- First set of images -->
          <div class="logo-loop-item">
            <img src="{% static 'images/single bed.png' %}" alt="1 Bed No Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/double room.png' %}" alt="2 Bed No Window Room" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/window room.png' %}" alt="1 Bed With Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/balcony.png' %}" alt="1 Bed With Balcony" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/condotel.png' %}" alt="2 Bed & Balcony Condotel" />
          </div>
          
          <!-- Duplicate set for seamless loop -->
          <div class="logo-loop-item">
            <img src="{% static 'images/single bed.png' %}" alt="1 Bed No Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/double room.png' %}" alt="2 Bed No Window Room" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/window room.png' %}" alt="1 Bed With Window" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/balcony.png' %}" alt="1 Bed With Balcony" />
          </div>
          <div class="logo-loop-item">
            <img src="{% static 'images/condotel.png' %}" alt="2 Bed & Balcony Condotel" />
          </div>
        </div>
      </div>
      
      <style>
        .logo-loop-container {
          width: 100%;
          overflow: hidden;
          position: relative;
          padding: 40px 0;
          background: linear-gradient(to right, rgba(248, 248, 248, 1) 0%, transparent 10%, transparent 90%, rgba(248, 248, 248, 1) 100%);
        }
        
        .logo-loop-track {
          display: flex;
          gap: 60px;
          animation: scroll 22s linear infinite;
          will-change: transform;
        }
        
        .logo-loop-item {
          flex-shrink: 0;
          transition: transform 0.3s ease;
        }
        
        .logo-loop-item:hover {
          transform: scale(1.1);
        }
        
        .logo-loop-item img {
          height: 280px;
          width: auto;
          object-fit: cover;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(calc(-50%));
          }
        }
        
        @media (max-width: 768px) {
          .logo-loop-item img {
            height: 200px;
          }
          
          .logo-loop-track {
            gap: 30px;
          }
        }
      </style>
    </section>
    <!-- END section -->
'@

$roomsHtml = $roomsHtml -replace [regex]::Escape($oldSectionRooms), $newSectionRooms
Set-Content -Path "site1\templates\rooms.html" -Value $roomsHtml -Encoding UTF8 -NoNewline
Write-Host "✓ Replaced rooms section in rooms.html"

Write-Host "`n✅ Both files have been updated successfully!"
Write-Host "Backups: home.html.bak created"
