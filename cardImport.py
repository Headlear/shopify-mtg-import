#!/usr/bin/python

import shopify
import json
import time
import urllib
import logging
import unicodedata

# Sometimes TCGPlayer uses non-standard names for its sets. Library of fixes!
tcgSetURLFix = { "Limited Edition Alpha" : "alpha-edition", "Limited Edition Beta" : "beta-edition", "Magic 2010" : "magic-2010-(m10)", "Magic 2011" : "magic-2011-(m11)", "Magic 2012" : "magic-2012-(m12)", "Magic 2013" : "magic-2013-(m13)", "Magic 2014" : "magic-2014-m14", "Magic: The Gathering-Commander" : "commander" }

def handleize (text):
  handle = text.replace(',', '').replace('\'', '').replace(':', '').replace('.', '').replace(' ', '-')
  handle = handle.lower()
  print "    Handle: " + handle
  return handle

def getTCGPlayerPrices(cardName, cardSet):

  if cardSet in tcgSetURLFix:
    cardSet = tcgSetURLFix[cardSet]
  
  #   Open the TCGPlayer URL
  tcgPlayerURL = "http://store.tcgplayer.com/magic/" + handleize(cardSet) + "/" + handleize(unicodedata.normalize('NFKD',cardName).encode('ascii','ignore'))

  htmlFile = urllib.urlopen(tcgPlayerURL)
  rawHTML = htmlFile.read()

  #   Scrape for the mid price
  tempIndex = rawHTML.find('<b>Normal')
  tempIndex= rawHTML.find('>Median:', tempIndex)
  startMidIndex = rawHTML.find("$", tempIndex)
  endMidIndex = rawHTML.find("<", startMidIndex)
  
  price = rawHTML[startMidIndex:endMidIndex]

  # #   Scrape for the foil mid price
  # tempIndex = rawHTML.find('<b>Foil')
  # tempIndex= rawHTML.find('>Median:', tempIndex)
  # startMidIndex = rawHTML.find("$", tempIndex)
  # endMidIndex = rawHTML.find("<", startMidIndex)
  
  # foilPrice = rawHTML[startMidIndex:endMidIndex]

  return price

def adjustPrice(price, iteration):
  newPrice = 0
  if len(price) > 0:
    newPrice = (1 - (0.1 * float(iteration))) * float(price.replace(',','').strip('$')) #Decrese value by 10% per iteration
  return newPrice


shop_url = "https://7d2a4105a61e881f5ab17389192243f2:07989a2032025d99db86729cc1703150@card-castle-games.myshopify.com/admin"
shopify.ShopifyResource.set_site(shop_url)

shop = shopify.Shop.current

jsonData = open('AllSetsArray.json')
data = json.load(jsonData)
jsonData.close()

conditions = ["NM/M", "SP", "MP"]

# Create a new product
i = 2
while i < len(data):

  print "SET ===== " + (data[i]["name"]) + " -- Set Skip Code: " + str(i)

  for j in range(0, len(data[i]["cards"])):
    print (unicode(data[i]["cards"][j]["name"]))
    #API CALL - Get a list of any products with the same handle. Should only ever return 1 result. Checking for dupes / variants
    print "    API Call."
    product = shopify.Product.find(handle="%s" % handleize(data[i]["cards"][j]["name"]))
    print "    Got API response." + str(product)

    if data[i]["cards"][j]["name"] != "Plains" && data[i]["cards"][j]["name"] != "Island" && data[i]["cards"][j]["name"] != "Swamp" && data[i]["cards"][j]["name"] != "Mountain" && data[i]["cards"][j]["name"] != "Forest":
      print "    Skipping basic land"
    else:
      if len(product) == 0:
        print "    New Card!"
        newProduct = shopify.Product()
        newProduct.title = data[i]["cards"][j]["name"]
        newProduct.product_type = data[i]["cards"][j]["type"]
        newProduct.vendor = data[i]["cards"][j]["rarity"]
        newProduct.images = [ { "src" : "http://mtgimage.com/multiverseid/%i.jpg" % data[i]["cards"][j]["multiverseid"] } ]
        newProduct.options = [{ "name" : "Set" },  { "name": "Condition" }]
        
        print "    Looking up prices..."
        newProduct.variants = [] 
        priceList = getTCGPlayerPrices(data[i]["cards"][j]["name"], data[i]["name"])
        newMetafields = [{ "namespace" : "card-importer", "key" : "artist", "value_type" : "string", "value" : "%s" % data[i]["cards"][j]["artist"]}, { "namespace" : "card-importer", "key" : "rarity", "value_type" : "string", "value" : "%s" % data[i]["cards"][j]["rarity"]}]
        if "flavor" in data[i]["cards"][j]:
          newMetafields.append({"namespace" : "card-importer", "key" : "flavor", "value_type" : "string", "value" : "%s" % data[i]["cards"][j]["flavor"]})

        print "    Creating variants"
        for k in range(0, len(conditions)):
          #Cards in all 4 conditions
          adjustedPrice = adjustPrice(priceList, float(k))
          variant = shopify.Variant(dict(option1=data[i]["name"], option2=conditions[k], price=adjustedPrice, metafields = newMetafields, sku=data[i]["cards"][j]["multiverseid"], grams=2, inventory_management="shopify", inventory_quantity=0))
          if "number" in data[i]["cards"][j]:
            variant.barcode = data[i]["cards"][j]["number"]
          newProduct.variants.append(variant)

        print "    Tagging the product"
        #Tag the product with EVERYTHING
        newProduct.tags = ""
        if "colors" in data[i]["cards"][j]:
          newProduct.tags = ",".join(data[i]["cards"][j]["colors"])
        if "rarity" in data[i]["cards"][j]:
          newProduct.tags = newProduct.tags + "," + data[i]["cards"][j]["rarity"]
        if "supertypes" in data[i]["cards"][j]:
          newProduct.tags = newProduct.tags + "," + ",".join(data[i]["cards"][j]["supertypes"])
        if "types" in data[i]["cards"][j]:
          newProduct.tags = newProduct.tags + "," + ",".join(data[i]["cards"][j]["types"])
        if "subtypes" in data[i]["cards"][j]:
          newProduct.tags = newProduct.tags + "," + ",".join(data[i]["cards"][j]["subtypes"])
        if "cmc" in data[i]["cards"][j]:
          newProduct.tags = newProduct.tags + "," + "cmc-" + str(data[i]["cards"][j]["cmc"])
        if "artist" in data[i]["cards"][j]:
          newProduct.tags = newProduct.tags + "," + data[i]["cards"][j]["artist"]

        print "    Building product description"
        #Create the product description
        productDescription = ""
        productDescription = productDescription + ('<div class="label">Card Name:</div><div class="value">%s</div>' % data[i]["cards"][j]["name"])
        if "manaCost" in data[i]["cards"][j]:
          manaSymbols = data[i]["cards"][j]["manaCost"].replace('{', ' ').replace('}', ' ')
          manaSymbols = manaSymbols.split()
          productDescription = productDescription + ('<div class="label">Mana Cost:</div><div class="value">')
          for symbol in manaSymbols:
            productDescription = productDescription + ('<i class="mana-%s"></i>' % symbol)
          productDescription = productDescription + ("</div>")
          productDescription = productDescription + ('<div class="label">CMC:</div><div class="value">%s</div>' % data[i]["cards"][j]["cmc"])
        productDescription = productDescription + ('<div class="label">Type:</div><div class="value">%s</div>' % data[i]["cards"][j]["type"])
        productDescription = productDescription + ('<div class="label">Rarity:</div><div class="value rarity"></div>') #Empty - waiting for JS to fill in
        if "text" in data[i]["cards"][j]:
          productDescription = productDescription + ('<div class="label">Card Text:</div><div class="value">%s</div>' % data[i]["cards"][j]["text"])
        if "power" in data[i]["cards"][j]:
         productDescription = productDescription + ('<div class="label">Power/Toughness:</div><div class="value">%s/%s</div>' % (data[i]["cards"][j]["power"], data[i]["cards"][j]["toughness"]))
        if "flavor" in data[i]["cards"][j]:
          productDescription = productDescription + ('<div class="label">Flavor:</div><div class="value flavor"></div>') #Empty - waiting for JS to fill in
        productDescription = productDescription + ('<div class="label">Artist:</div><div class="value artist"></div>') #Empty - waiting for JS to fill in
        if "number" in data[i]["cards"][j]:
          productDescription = productDescription + ('<div class="label">Collector\'s Number:</div><div class="value number"></div>') #Empty - waiting for JS to fill in
        newProduct.body_html = productDescription

        #API CALL - Create the product
        print "    API Call."
        newProduct.save()
        print "    Product ID: " + str(newProduct.id)

        print "    Adding product to category"
        #API CALL - Add the product to the set collection
        setCollection = shopify.CustomCollection.find(handle="%s" % handleize(data[i]["name"]))
        collect = shopify.Collect({ "product_id" : newProduct.id, "collection_id" : setCollection[0].id })
        collect.save()
        print "    Got API response."

      else:
        print "    Duplicate / Variant Detected -- MultiverseID: " + str(data[i]["cards"][j]["multiverseid"])

        isNew = 1
        for variant in product[0].variants:
          if isNew == 0:
            break
          if data[i]["cards"][j]["multiverseid"] == int(variant.sku):
            isNew=0
            print "    Duplicate -- SKU: " + str(variant.sku)

        if isNew:
          print "    Adding image for new printing"
          product[0].images.append({ "src" : "http://mtgimage.com/multiverseid/%i.jpg" % data[i]["cards"][j]["multiverseid"] })

          print "    Looking up prices..."
          priceList = getTCGPlayerPrices(data[i]["cards"][j]["name"], data[i]["name"])
          newMetafields = [{ "namespace" : "card-importer", "key" : "artist", "value_type" : "string", "value" : "%s" % data[i]["cards"][j]["artist"]}, { "namespace" : "card-importer", "key" : "rarity", "value_type" : "string", "value" : "%s" % data[i]["cards"][j]["rarity"]}]
          if "flavor" in data[i]["cards"][j]:
            newMetafields.append({"namespace" : "card-importer", "key" : "flavor", "value_type" : "string", "value" : "%s" % data[i]["cards"][j]["flavor"]})

          print "    Creating variants"
          for k in range(0, len(conditions)):
            #Cards in all 4 conditions
            adjustedPrice = adjustPrice(priceList, float(k))
            variant = shopify.Variant(dict(option1=data[i]["name"], option2=conditions[k], price=adjustedPrice, metafields = newMetafields, sku=data[i]["cards"][j]["multiverseid"], grams=2, inventory_management="shopify", inventory_quantity=0))
            if "number" in data[i]["cards"][j]:
              variant.barcode = data[i]["cards"][j]["number"]
            product[0].variants.append(variant)
          
          print "    Tagging product"
          if "rarity" in data[i]["cards"][j] and data[i]["cards"][j]["rarity"] not in product[0].tags:
            product[0].tags = product[0].tags + "," + data[i]["cards"][j]["rarity"]
          if "artist" in data[i]["cards"][j] and data[i]["cards"][j]["artist"] not in product[0].tags:
            product[0].tags = product[0].tags + "," + data[i]["cards"][j]["artist"]

          #API CALL - Save the variants and tags to the product
          product[0].save()
          print "    Got API response."

          print "    Adding product to category"
          #API CALL - Add the product to the set collection
          setCollection = shopify.CustomCollection.find(handle="%s" % handleize(data[i]["name"]))
          collect = shopify.Collect({ "product_id" : product[0].id, "collection_id" : setCollection[0].id })
          collect.save()
          print "    Got API response."
        else:
          print "    Waiting..."
          time.sleep(0.5)

  i += 1
#   success = newProduct.save() #returns false if the record is invalid
# # or
# if newProduct.errors:
#     #something went wrong, see newProduct.errors.full_messages() for example

