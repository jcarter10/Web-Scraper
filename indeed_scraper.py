from bs4 import BeautifulSoup
import urllib.request
import pandas as pd
import time
import sys


def main():
    
    # variables
    num_of_entries = 25
    csv_name = 'indeed.csv'
    column_names = ['url', 'job_title', 'company', 'location', 'remote_option', 'salary', 'type', 'description']
    result_df = pd.DataFrame(columns = column_names)

    # ask user for # of entries
    user_input = input("Enter the # of job pages you wish to scrape (min: 1, max: 100, default: 25): ")
    
    # use users # of entries if declared, uses default if not
    if user_input != '':
        num_of_entries = int(user_input)
        
        # make sure user input is in range
        if num_of_entries < 1 or num_of_entries > 100:
            print('Bad input value, try again.')
            sys.exit(0)

    print('Each request will be delayed by two seconds due to web scraping ethics.\nScraping ' + str(num_of_entries) + ' job pages...')

    # grab page content from url
    url = 'https://ca.indeed.com/jobs?q=&l=remote'
    sliders = get_job_panels(url)

    # for each slider, go to job page and extract information
    i = 1
    for slider in sliders:

        # create url for current slider to go to
        a_tag = slider.find_previous('a', href=True)
        jobpage_url = 'https://ca.indeed.com' + a_tag['href']

        # get html of page
        jobpage = urllib.request.urlopen(jobpage_url)
        jobpage_HTML = BeautifulSoup(jobpage, 'html.parser')

        # extract wanted information from page
        result_df = result_df.append(extractInfo(jobpage_url, jobpage_HTML, column_names), ignore_index=True)

        # calculating percentage of completion and printing to screen
        percentage = (i / num_of_entries) * 100
        sys.stdout.write("\rCompletion: %.1f %% " % percentage)
        sys.stdout.flush()

        # stop when entry limit is reached
        if i == num_of_entries:
            break
        else:
            i += 1

        # when the current page runs out of sliders, go to new page and get sliders 
        if i == len(sliders):
            # get link to next page
            url = get_next_page(url)
            url = 'https://ca.indeed.com' + url

            # attach new job slider panels onto current to continue loop
            sliders.extend(get_job_panels(url))

        # for web scraping ethics, add a 2 second delay between each scrape request
        time.sleep(2)

    # saving final dataframe to csv
    result_df.index.name = 'index'
    result_df.to_csv('results/' + csv_name, index=True)

    print('\nFinished!')


# gets all the job panels for current page
def get_job_panels(url):
    
    # open url for current page 
    page = urllib.request.urlopen(url)

    # parse the pages html
    soup = BeautifulSoup(page, 'html.parser')

    # grab every content slider
    result_table = soup.find('div', attrs={'id': 'mosaic-zone-jobcards'})
    sliders = result_table.find_all('div', attrs={'class': 'slider_container'})

    return sliders


# grabs pagination link for navigating to next page
def get_next_page(url):

     # open url for current page 
    page = urllib.request.urlopen(url)

    # parse the pages html
    html = BeautifulSoup(page, 'html.parser')

    # parse to pagination at bottom of page
    links = html.find('ul', attrs={'class': 'pagination-list'})
    links = links.find_all('li')
    
    # find href for next button in pagination
    link = links[len(links) - 1].find('a', href=True)
    return link['href']


# examine the passed html and parse it to extract wanted information.
def extractInfo(url, html, column_names):
    
    # create html pointers for easier parsing
    job_title_pointer = html.find(
        'div', attrs={'class': 'jobsearch-DesktopStickyContainer'})
    job_location_pointer = html.find(
        'div', attrs={'class': 'jobsearch-CompanyInfoWithoutHeaderImage'})
    job_details_pointer = html.find(
        'div', attrs={'class': 'jobsearch-JobMetadataHeader-item'})
    job_description_pointer = html.find(
        'div', attrs={'id': 'jobDescriptionText'})

    # job title
    job_title = job_title_pointer.find_next('div')
    job_title = job_title.find('h1', attrs={
                               'class': 'icl-u-xs-mb--xs icl-u-xs-mt--none jobsearch-JobInfoHeader-title'}).text

    # company name
    company_name = job_location_pointer.find(
        'div', attrs={'class': 'icl-u-lg-mr--sm icl-u-xs-mr--xs'})
    company_name = company_name.text

    # if they exist, get location and remote option
    location_pointer = job_location_pointer.find('div', attrs={
                                                 'class': 'icl-u-xs-mt--xs icl-u-textColor--secondary jobsearch-JobInfoHeader-subtitle jobsearch-DesktopStickyContainer-subtitle'})
    location_pointer = location_pointer.contents

    if ('remote' or 'temporary remote') in location_pointer[len(location_pointer) - 1].text.lower():
        location_name = location_pointer[len(location_pointer) - 2].text
        location_remote = location_pointer[len(location_pointer) - 1].text
    else:
        location_name = location_pointer[len(location_pointer) - 1].text
        location_remote = 'No'

    # if they exist, get salary and type
    if job_details_pointer == None:
        job_salary = 'N/A'
        job_type = 'N/A'
    else:
        job_detail_content = job_details_pointer.contents
        
        # only salary or type exist
        if len(job_detail_content) == 1:

            # element contains a number, so it's salary
            for char in job_detail_content[0].text:
                if char.isdigit():
                    job_type = 'N/A'
                    job_salary = (job_detail_content[0].text).replace(
                        '-', '').lstrip()
                    break
            # no number found, so it's job type
            else:
                job_type = job_detail_content[0].text
                job_salary = 'N/A'

        # both salary and type exist
        else:
            job_salary = job_detail_content[0].text
            job_type = (job_detail_content[1].text).replace('-', '', 1).lstrip()

    # grab job details
    text = job_description_pointer.find_all(text=True)
    job_description = ' \n'.join([str(t) for t in text])
    job_description = '"' + job_description + '"'

    # return page results as a dataframe
    df = {
        column_names[0]: [url], 
        column_names[1]: [job_title], 
        column_names[2]: [company_name],
        column_names[3]: [location_name],
        column_names[4]: [location_remote],
        column_names[5]: [job_salary],
        column_names[6]: [job_type],
        column_names[7]: [job_description]
    }
    return pd.DataFrame(data=df)


if __name__ == '__main__':
    main()
