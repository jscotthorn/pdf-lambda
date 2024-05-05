import json
import tempfile
import os
import fitz
import urllib.request
import re

def lambda_handler(event, context):
    """ The main function for AWS Lambda to invoke.
    
    This takes a url query parameter to a PDF, parses it into text, and returns the text 
    with a list of extracted references to other OAG citations.
    """

    # Passed params
    url = event["queryStringParameters"]['url']
    citation = event["queryStringParameters"]['citation']

    # Custom headers to avoid 403 errors while scraping.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://www.ag.ky.gov/Resources/orom/Pages/default.aspx',
        'Sec-Ch-Ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"'
    }

    # Create a Request object with the URL and headers
    req = urllib.request.Request(url, headers=headers)

    try:
        # Use the Request object with urlopen
        with urllib.request.urlopen(req) as response:
            # Create a temporary file with a .pdf suffix
            fileTemp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            # Read the content
            file_content = response.read()
            # Write the content to the temporary file
            fileTemp.write(file_content)

        # Close the temporary file
        fileTemp.close()

        record = {}
        record['text'] = pdf_to_text(fileTemp.name, citation)
    finally:
        os.remove(fileTemp.name)

    reference_map = extract_oag_references(record['text']);
    record['references'] = list(reference_map.keys())
    # Check if the current citations is in the list and remove it
    if citation in record['references']:
        record['references'].remove(citation)

    return {
        'statusCode': 200,
        'body': json.dumps(record)
    }

def pdf_to_text(pdf_path, oag_citation):
    """ Convert a PDF to searchable text 
    """
    pdf_document = fitz.open(pdf_path)
    content = ""
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        text = page.get_text("text")
        # Use regex to clean up whitespace and line breaks
        cleaned_text = re.sub(r'\n\s*\n', r'\n\n', text.strip(), flags=re.M)
        
        # Remove page numbers originating from footer
        cleaned_text = re.sub(oag_citation + r'\s+Page \d+\s+', ' ', cleaned_text, flags=re.M).strip()
        content += f"{cleaned_text}"
    pdf_document.close()
    return content

def extract_and_format_oag_citation(metadata):
    """ Function to extract the first OAG citation found from text
    Can be any of these, variable numbers & digit amount (1-4):
    OAG 78-823
    OAG 78 339
    OAG 2020-01
    OAG17-021
    OAG No. 04-005
    0AG 95-17
    Oag 03-003
    No. 80-320
    No. OAG 80 349
    No. 15-OAG-003
    87-71
    90-5
    96-ORD-43
    96-OMD-43
    ORD 97-132
    OMD 97-124
    Open Records Log Number 200000214
    [NO NUMBER IN ORIGINAL]
    """
    if isinstance(metadata, str) == False:
        return None
    if '[NO NUMBER IN ORIGINAL]' in metadata:
        return '[NO NUMBER IN ORIGINAL]'
    # Special Format Open Records Log Number 200000214
    match = re.search(r'Open Records Log Number (\d+)', metadata)
    if match:
        return match[0]
    # Format 96-ORD-43
    match = re.search(r'(\d{2,3})-ORD-(\d{1,3})', metadata)
    if match:
        return '{}-ORD-{}'.format(match[1], match[2].zfill(3))
    # Format ORD 97-132
    match = re.search(r'ORD (\d{2,3})-(\d{1,3})', metadata)
    if match:
        return '{}-ORD-{}'.format(match[1], match[2].zfill(3))
    # Format 96-OMD-43
    match = re.search(r'(\d{1,3})-OMD-(\d{1,3})', metadata)
    if match:
        return '{}-OMD-{}'.format(match[1], match[2].zfill(3))
    # Format OMD 97-124
    match = re.search(r'OMD (\d{2,3})-(\d{1,3})', metadata)
    if match:
        return '{}-OMD-{}'.format(match[1], match[2].zfill(3))
    # Format OAG 78-823, OAG 2020-01, OAG17-021, OAG17-021, OAG No. 04-005, 0AG 95-17, Oag 03-003
    match = re.search(r'[O0][Aa][Gg] ?(No. )?(\d{1,4})[ \-](\d{1,3})', metadata)
    if match:
        return 'OAG {}-{}'.format(match[2], match[3].zfill(3 if int(match[2]) < 20 else 2))
    # Format No. 80-320, No. OAG 80 349, 87-71
    match = re.search(r'No. (OAG )?(\d{1,2})[ \-](\d{1,3})', metadata)
    if match:
        return 'OAG {}-{}'.format(match[2], match[3].zfill(3 if int(match[2]) < 20 else 2))
    # Format No. 15-OAG-003
    match = re.search(r'No. (\d{1,4})-OAG-(\d{1,3})', metadata)
    if match:
        return 'OAG {}-{}'.format(match[1], match[2].zfill(3 if int(match[2]) < 20 else 2))
    # Format 87-71, 90-5
    match = re.search(r'\s+(\d{2})-(\d{1,3})\s+', metadata)
    if match:
        return 'OAG {}-{}'.format(match[1], match[2].zfill(3 if int(match[2]) < 20 else 2))
    return None;
    
def extract_oag_references(input_string):
    """ We want to extract references to other cases
    """
    # Initialize an empty dictionary to store all matches and their source strings
    all_matches = {}
    
    # Some opinions reference multiple:
    # OAGs 84-22, 84-36, and 84-203
    # (OAG) 84-22; 84-36; 84-203
    matches = re.finditer('OAG[s\)\]]? (\d{2,4}\-\d{1,3}[,;]? (and)? ?)+', input_string, re.MULTILINE)
    for match in matches:
        group = match.group()
        multiples = re.finditer('\d{2}-\d{1-3}', group)
        for item in multiples:
            numbers = match.group()
            formatted_match = extract_and_format_oag_citation('OAG ' + numbers)
            if formatted_match not in all_matches:
                all_matches[formatted_match] = [numbers]
            elif group not in all_matches[formatted_match]:
                all_matches[formatted_match].extend(numbers)
    
    # Other patterns are for single referencs to OAGs, ORD, or OMDs.
    patterns = [
        r'((\d{2,3})-ORD-(\d{1,3}))',
        r'(ORD (\d{2,3})-(\d{1,3}))',
        r'((\d{2,3})-OMD-(\d{1,3}))',
        r'(OMD (\d{2,3})-(\d{1,3}))',
        r'([O0][Aa][Gg] ?N?o?\.? ?(\d{2,4})[ \-](\d{1,3}))',
    ]
    
    # Iterate over each pattern
    for pattern in patterns:
        matches = re.finditer(pattern, input_string, re.MULTILINE)

        # Add the formatted matches to the all_matches dictionary
        for match in matches:
            group = match.group()
            formatted_match = extract_and_format_oag_citation(group)
            if formatted_match not in all_matches:
                all_matches[formatted_match] = [group]
            elif group not in all_matches[formatted_match]:
                all_matches[formatted_match].extend(group)
        
    #print('all_matches', all_matches)
    return all_matches
